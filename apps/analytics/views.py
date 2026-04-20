from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from io import BytesIO

from utils.permissions import HRTEVOrAdminPermission
from .services import generate_analytics_excel
from apps.students.models import CATEGORY_CHOICES, Student
from apps.students.models import LevelHistory
from apps.hr_calls.models import HrCall
from apps.students.serializers_short import StudentShortSerializer


class BaseAnalyticsDashboardView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    
    # Фильтр по категориям, переопределяется в дочерних классах
    category_filter = None
    
    def get_filtered_queryset(self):
        qs = Student.objects.all()
        if self.category_filter is not None:
            if isinstance(self.category_filter, (list, tuple)):
                qs = qs.filter(category__in=self.category_filter)
            else:
                qs = qs.filter(category=self.category_filter)
        return qs
    
    def get(self, request):
        # Optional period analytics: ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
        date_from_raw = request.query_params.get("date_from")
        date_to_raw = request.query_params.get("date_to")
        
        base_url = request.build_absolute_uri('/api/v1/analytics/metrics/students/')

        # Собираем данные для аналитики
        students_qs = self.get_filtered_queryset()
        total_students = students_qs.count()
        active_students = students_qs.filter(status='active').exclude(level='fired').count()
        fired_students = students_qs.filter(status='fired').count()
        
        # HR-вызовы за последний месяц
        from django.utils import timezone
        from datetime import timedelta
        month_ago = timezone.now() - timedelta(days=30)
        student_ids = students_qs.values_list('id', flat=True)
        called_hr_students = HrCall.objects.filter(
            created_at__gte=month_ago,
            person_type='cat',
            student_id__in=student_ids
        ).count()
        
        # Новые студенты за месяц
        new_students_total = students_qs.filter(created_at__gte=month_ago).count()
        
        # Изменения уровней за месяц
        level_changes_total = LevelHistory.objects.filter(
            changed_at__gte=month_ago,
            student_id__in=student_ids
        ).count()
        
        # Распределение по уровням
        distribution_by_level = {}
        for student in students_qs.filter(status='active').exclude(level='fired'):
            level = student.level
            if level in distribution_by_level:
                distribution_by_level[level] += 1
            else:
                distribution_by_level[level] = 1
        
        # Распределение по статусам
        distribution_by_status = {}
        for student in students_qs.all():
            status = student.status
            if status in distribution_by_status:
                distribution_by_status[status] += 1
            else:
                distribution_by_status[status] = 1
        
        # Распределение по категориям
        distribution_by_category = {}
        for student in students_qs.all():
            category = student.category
            if category in distribution_by_category:
                distribution_by_category[category] += 1
            else:
                distribution_by_category[category] = 1

        period_stats = None
        if date_from_raw and date_to_raw:
            try:
                date_from = datetime.strptime(date_from_raw, "%Y-%m-%d").date()
                date_to = datetime.strptime(date_to_raw, "%Y-%m-%d").date()
                if date_from > date_to:
                    date_from, date_to = date_to, date_from
                start_dt = timezone.make_aware(datetime.combine(date_from, datetime.min.time()))
                end_dt = timezone.make_aware(datetime.combine(date_to, datetime.max.time()))

                # Подсчет уволенных по дате увольнения
                fired_students_period = students_qs.filter(
                    status='fired',
                    fired_date__isnull=False,
                    fired_date__range=(date_from, date_to)
                ).count()

                # Подсчет ВСЕХ вызовов к HR (независимо от решения проблемы)
                called_hr_total = HrCall.objects.filter(
                    created_at__range=(start_dt, end_dt),
                    person_type='cat',
                    student_id__in=student_ids
                ).count()
                
                new_students_period = students_qs.filter(
                    created_at__range=(start_dt, end_dt)
                ).count()
                
                level_changes_period = LevelHistory.objects.filter(
                    changed_at__range=(start_dt, end_dt),
                    student_id__in=student_ids
                ).count()

                period_stats = {
                    "date_from": date_from,
                    "date_to": date_to,
                    "new_students_total": new_students_period,
                    "level_changes_total": level_changes_period,
                    "fired_students_total": fired_students_period,
                    "called_hr_students_total": called_hr_total,
                    "metrics_urls": {
                        "fired": f"{base_url}?metric=fired&date_from={date_from}&date_to={date_to}",
                        "called_hr": f"{base_url}?metric=called_hr&date_from={date_from}&date_to={date_to}",
                        "new": f"{base_url}?metric=new&date_from={date_from}&date_to={date_to}",
                        "active": f"{base_url}?metric=active&date_from={date_from}&date_to={date_to}"
                    }
                }
            except Exception:
                period_stats = None
        
        active_total = active_students or 1
        students_by_level = []
        for level, count in distribution_by_level.items():
            percentage = round(count / active_total * 100, 1) if active_total > 0 else 0.0
            students_by_level.append({
                "level": level,
                "display_name": level.capitalize() if level else "Без Уровня",
                "count": count,
                "percentage": percentage,
                "students_url": f"{base_url}?metric=level_{level}"
            })
        total = total_students or 1
        students_by_status = [
            {
                "status": status,
                "display_name": status.capitalize(),
                "count": count,
                "percentage": round(count / total * 100, 1),
                "students_url": f"{base_url}?metric=status_{status}"
            }
            for status, count in distribution_by_status.items()
        ]
        students_by_category = [
            {
                "category": category,
                "display_name": dict(CATEGORY_CHOICES).get(category, category.capitalize()),
                "count": count,
                "percentage": round(count / total * 100, 1),
                "students_url": f"{base_url}?metric=category_{category}"
            }
            for category, count in distribution_by_category.items()
        ]
        
        # Общие ссылки на метрики
        metrics_urls = {
            "fired": f"{base_url}?metric=fired",
            "called_hr": f"{base_url}?metric=called_hr",
            "new": f"{base_url}?metric=new",
            "active": f"{base_url}?metric=active"
        }
        
        response_data = {
            "success": True,
            "total_students": total_students,
            "active_students": active_students,
            "fired_students": fired_students,
            "called_hr_students": called_hr_students,
            "new_students_total": new_students_total,
            "level_changes_total": level_changes_total,
            "period": period_stats,
            "students_by_level": students_by_level,
            "students_by_status": students_by_status,
            "students_by_category": students_by_category,
            "updated_at": timezone.now(),
            "metrics_urls": metrics_urls,
        }
        
        # Добавляем информацию о группе если это не полная аналитика
        if self.category_filter is not None:
            if self.category_filter == 'college':
                response_data['group'] = 'ap'
                response_data['group_name'] = 'Колледжисты (АП)'
            else:
                response_data['group'] = 'as_patriots'
                response_data['group_name'] = 'Алабуга Старт + Патриоты'
        
        return Response(response_data, status=200)


class AnalyticsDashboardView(BaseAnalyticsDashboardView):
    """Полная аналитика все категории вместе"""
    category_filter = None


class AnalyticsDashboardAPView(BaseAnalyticsDashboardView):
    """Аналитика только для Колледжистов (АП)"""
    category_filter = 'college'


class AnalyticsDashboardASPatriotsView(BaseAnalyticsDashboardView):
    """Аналитика только для Алабуга Старт + Патриоты"""
    category_filter = ['patriot', 'alabuga_start_rf', 'alabuga_start_sng', 'alabuga_mulatki']


class AnalyticsMetricsStudentsView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Получить список студентов по метрике"""
        metric = request.query_params.get("metric")
        date_from_raw = request.query_params.get("date_from")
        date_to_raw = request.query_params.get("date_to")
        
        queryset = Student.objects.all()
        
        # Стандартные метрики
        if metric == "fired":
            if date_from_raw and date_to_raw:
                date_from = datetime.strptime(date_from_raw, "%Y-%m-%d").date()
                date_to = datetime.strptime(date_to_raw, "%Y-%m-%d").date()
                queryset = queryset.filter(status='fired', fired_date__range=(date_from, date_to))
            else:
                queryset = queryset.filter(status='fired')
        elif metric == "called_hr":
            from django.utils import timezone
            from datetime import timedelta
            month_ago = timezone.now() - timedelta(days=30)
            student_ids = HrCall.objects.filter(
                created_at__gte=month_ago,
                person_type='cat',
                student__isnull=False
            ).values_list('student_id', flat=True)
            queryset = queryset.filter(id__in=student_ids)
        elif metric == "active":
            queryset = queryset.filter(status='active').exclude(level='fired')
        elif metric == "new":
            from django.utils import timezone
            from datetime import timedelta
            month_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(created_at__gte=month_ago)
        
        # Метрики по статусу
        elif metric.startswith('status_'):
            status = metric[7:]
            if status == 'active':
                queryset = queryset.filter(status='active').exclude(level='fired')
            else:
                queryset = queryset.filter(status=status)
        
        # Метрики по уровню
        elif metric.startswith('level_'):
            level = metric[6:]
            queryset = queryset.filter(level=level, status='active').exclude(level='fired')
        
        # Метрики по категории
        elif metric.startswith('category_'):
            category = metric[9:]
            queryset = queryset.filter(category=category)
        
        else:
            return Response({"success": False, "error": "Invalid metric"}, status=400)
        
        serializer = StudentShortSerializer(queryset, many=True)
        return Response({
            "success": True,
            "metric": metric,
            "count": queryset.count(),
            "students": serializer.data
        }, status=200)


class AnalyticsAPView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Аналитика только для Колледжистов (АП)"""
        queryset = Student.objects.filter(category='college')
        
        total_students = queryset.count()
        active_students = queryset.filter(status='active').exclude(level='fired').count()
        fired_students = queryset.filter(status='fired').count()
        
        # Распределение по уровням
        distribution_by_level = {}
        for student in queryset.filter(status='active').exclude(level='fired'):
            level = student.level
            if level in distribution_by_level:
                distribution_by_level[level] += 1
            else:
                distribution_by_level[level] = 1
        
        active_total = active_students or 1
        students_by_level = []
        for level, count in distribution_by_level.items():
            percentage = round(count / active_total * 100, 1) if active_total > 0 else 0.0
            students_by_level.append({
                "level": level,
                "display_name": level.capitalize() if level else "Без Уровня",
                "count": count,
                "percentage": percentage
            })
        
        return Response({
            "success": True,
            "group": "college",
            "group_name": "Колледжисты (АП)",
            "total_students": total_students,
            "active_students": active_students,
            "fired_students": fired_students,
            "students_by_level": students_by_level,
            "updated_at": timezone.now(),
        }, status=200)


class AnalyticsASPatriotsView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Аналитика для Алабуга Старт + Патриоты"""
        queryset = Student.objects.filter(category__in=['patriot', 'alabuga_start_rf', 'alabuga_start_sng', 'alabuga_mulatki'])
        
        total_students = queryset.count()
        active_students = queryset.filter(status='active').exclude(level='fired').count()
        fired_students = queryset.filter(status='fired').count()
        
        # Распределение по уровням
        distribution_by_level = {}
        for student in queryset.filter(status='active').exclude(level='fired'):
            level = student.level
            if level in distribution_by_level:
                distribution_by_level[level] += 1
            else:
                distribution_by_level[level] = 1
        
        active_total = active_students or 1
        students_by_level = []
        for level, count in distribution_by_level.items():
            percentage = round(count / active_total * 100, 1) if active_total > 0 else 0.0
            students_by_level.append({
                "level": level,
                "display_name": level.capitalize() if level else "Без Уровня",
                "count": count,
                "percentage": percentage
            })
        
        return Response({
            "success": True,
            "group": "as_patriots",
            "group_name": "Алабуга Старт + Патриоты",
            "total_students": total_students,
            "active_students": active_students,
            "fired_students": fired_students,
            "students_by_level": students_by_level,
            "updated_at": timezone.now(),
        }, status=200)


class LevelDistributionView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        # Собираем данные для аналитики
        active_students = Student.objects.filter(status='active').exclude(level='fired')
        
        # Распределение по уровням
        distribution_by_level = {}
        for student in active_students:
            level = student.level
            if level in distribution_by_level:
                distribution_by_level[level] += 1
            else:
                distribution_by_level[level] = 1
        
        active_total = active_students.count() or 1
        levels = [
            {
                "level": level,
                "display_name": level.capitalize(),
                "count": count,
                "percentage": round(count / active_total * 100, 1)
            }
            for level, count in distribution_by_level.items()
        ]
        return Response({
            "success": True,
            "levels": levels,
            "total_active": active_total
        }, status=200)


class AnalyticsDownloadView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    
    def get(self, request, *args, **kwargs):
        """
        Скачивание аналитики через API.
        Параметры:
        - type: 'full' - полная аналитика, 'month' - аналитика за месяц
        - month: период в формате YYYY-MM (для type=month)
        - date_from: начало периода YYYY-MM-DD (для произвольного периода)
        - date_to: конец периода YYYY-MM-DD (для произвольного периода)
        """
        # Получаем фильтр по категории если он передан из urls.py
        category_filter = kwargs.get('category_filter', None)
        
        download_type = request.GET.get('type', 'full')
        month_raw = request.GET.get('month')
        date_from_raw = request.GET.get("date_from")
        date_to_raw = request.GET.get("date_to")
        
        date_from = None
        date_to = None
        
        # Обработка параметра month (формат YYYY-MM)
        if month_raw:
            try:
                year, month_num = map(int, month_raw.split('-'))
                date_from = date(year, month_num, 1)
                if month_num == 12:
                    date_to = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    date_to = date(year, month_num + 1, 1) - timedelta(days=1)
            except (ValueError, IndexError):
                return Response({"error": "Invalid month format. Use YYYY-MM."}, status=400)
        # Обработка параметров date_from и date_to
        elif date_from_raw and date_to_raw:
            try:
                date_from = datetime.strptime(date_from_raw, "%Y-%m-%d").date()
                date_to = datetime.strptime(date_to_raw, "%Y-%m-%d").date()
                if date_from > date_to:
                    date_from, date_to = date_to, date_from
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        
        # Генерация Excel-файла
        wb = generate_analytics_excel(download_type, date_from, date_to)
        
        # Сохранение в буфер
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Формирование имени файла
        now = timezone.now()
        if download_type == 'full':
            filename = f"Analytics_cats_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:
            if date_from and date_to:
                filename = f"Analytics_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}.xlsx"
            else:
                filename = f"Analytics_{now.strftime('%Y%m')}_month_{now.strftime('%H%M%S')}.xlsx"
        
        # Создание HTTP-ответа
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response


class LevelDistributionAPView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Аналитика по уровням только для АП (Колледжисты)"""
        active_students = Student.objects.filter(
            status='active',
            category='college'
        ).exclude(level='fired')
        
        distribution_by_level = {}
        for student in active_students:
            level = student.level
            if level in distribution_by_level:
                distribution_by_level[level] += 1
            else:
                distribution_by_level[level] = 1
        
        active_total = active_students.count() or 1
        levels = [
            {
                "level": level,
                "display_name": level.capitalize() if level else "Без Уровня",
                "count": count,
                "percentage": round(count / active_total * 100, 1)
            }
            for level, count in distribution_by_level.items()
        ]
        return Response({
            "success": True,
            "group": "ap",
            "group_name": "Колледжисты (АП)",
            "levels": levels,
            "total_active": active_total
        }, status=200)


class LevelDistributionASPatriotsView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Аналитика по уровням только для АС + Патриоты"""
        active_students = Student.objects.filter(
            status='active',
            category__in=['patriot', 'alabuga_start_rf', 'alabuga_start_sng', 'alabuga_mulatki']
        ).exclude(level='fired')
        
        distribution_by_level = {}
        for student in active_students:
            level = student.level
            if level in distribution_by_level:
                distribution_by_level[level] += 1
            else:
                distribution_by_level[level] = 1
        
        active_total = active_students.count() or 1
        levels = [
            {
                "level": level,
                "display_name": level.capitalize() if level else "Без Уровня",
                "count": count,
                "percentage": round(count / active_total * 100, 1)
            }
            for level, count in distribution_by_level.items()
        ]
        return Response({
            "success": True,
            "group": "as_patriots",
            "group_name": "Алабуга Старт + Патриоты",
            "levels": levels,
            "total_active": active_total
        }, status=200)


class QuarterlyAnalyticsView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Квартальная аналитика (все категории вместе)"""
        # TODO: Реализация квартальной аналитики (оставляем как было)
        return Response({"success": True, "message": "Quarterly analytics all categories"}, status=200)


class QuarterlyAnalyticsAPView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Квартальная аналитика только для АП"""
        return Response({"success": True, "group": "ap", "message": "Quarterly analytics for AP"}, status=200)


class QuarterlyAnalyticsASPatriotsView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        """Квартальная аналитика только для АС + Патриоты"""
        return Response({"success": True, "group": "as_patriots", "message": "Quarterly analytics for AS + Patriots"}, status=200)


def analytics_download_view(request):
    """Функция для скачивания аналитики без API"""
    from django.contrib.auth.decorators import login_required
    from django.contrib.admin.views.decorators import staff_member_required
    
    @staff_member_required
    def inner_view(request):
        download_type = request.GET.get('type', 'full')
        month = request.GET.get('month')
        
        date_from = None
        date_to = None
        
        if month:
            try:
                # Формат YYYY-MM
                year, month_num = map(int, month.split('-'))
                date_from = date(year, month_num, 1)
                if month_num == 12:
                    date_to = date(year + 1, 1, 1)
                else:
                    date_to = date(year, month_num + 1, 1)
                date_to = date_to - timedelta(days=1)
            except (ValueError, IndexError):
                return HttpResponse("Invalid month format. Use YYYY-MM.", status=400)
        
        # Генерация Excel-файла
        wb = generate_analytics_excel(download_type, date_from, date_to)
        
        # Сохранение в буфер
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Формирование имени файла
        now = timezone.now()
        if download_type == 'full':
            filename = f"Analytics_cats_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:
            if date_from and date_to:
                filename = f"Analytics_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}.xlsx"
            else:
                filename = f"Analytics_{now.strftime('%Y%m')}_month_{now.strftime('%H%M%S')}.xlsx"
        
        # Создание HTTP-ответа
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    return inner_view(request)
