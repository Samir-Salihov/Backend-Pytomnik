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


class AnalyticsDashboardView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    def get(self, request):
        # Optional period analytics: ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
        date_from_raw = request.query_params.get("date_from")
        date_to_raw = request.query_params.get("date_to")

        # Собираем данные для аналитики
        total_students = Student.objects.count()
        active_students = Student.objects.filter(status='active').exclude(level='fired').count()
        fired_students = Student.objects.filter(status='fired').count()
        
        # HR-вызовы за последний месяц
        from django.utils import timezone
        from datetime import timedelta
        month_ago = timezone.now() - timedelta(days=30)
        called_hr_students = HrCall.objects.filter(
            created_at__gte=month_ago,
            person_type='cat'
        ).count()
        
        # Новые студенты за месяц
        new_students_total = Student.objects.filter(created_at__gte=month_ago).count()
        
        # Изменения уровней за месяц
        level_changes_total = LevelHistory.objects.filter(changed_at__gte=month_ago).count()
        
        # Распределение по уровням
        distribution_by_level = {}
        for student in Student.objects.filter(status='active').exclude(level='fired'):
            level = student.level
            if level in distribution_by_level:
                distribution_by_level[level] += 1
            else:
                distribution_by_level[level] = 1
        
        # Распределение по статусам
        distribution_by_status = {}
        for student in Student.objects.all():
            status = student.status
            if status in distribution_by_status:
                distribution_by_status[status] += 1
            else:
                distribution_by_status[status] = 1
        
        # Распределение по категориям
        distribution_by_category = {}
        for student in Student.objects.all():
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
                fired_students_period = Student.objects.filter(
                    status='fired',
                    fired_date__isnull=False,
                    fired_date__range=(date_from, date_to)
                ).count()

                # Подсчет ВСЕХ вызовов к HR (независимо от решения проблемы)
                called_hr_total = HrCall.objects.filter(
                    created_at__range=(start_dt, end_dt),
                    person_type='cat'
                ).count()

                period_stats = {
                    "date_from": date_from,
                    "date_to": date_to,
                    "new_students_total": Student.objects.filter(created_at__range=(start_dt, end_dt)).count(),
                    "level_changes_total": LevelHistory.objects.filter(changed_at__range=(start_dt, end_dt)).count(),
                    "fired_students_total": fired_students_period,
                    "called_hr_students_total": called_hr_total,
                }
            except Exception:
                period_stats = None
        
        active_total = active_students or 1
        students_by_level = []
        for level, count in distribution_by_level.items():
            percentage = round(count / active_total * 100, 1) if active_total > 0 else 0.0
            students_by_level.append({
                "level": level,
                "display_name": level.capitalize(),
                "count": count,
                "percentage": percentage
            })
        total = total_students or 1
        students_by_status = [
            {
                "status": status,
                "display_name": status.capitalize(),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for status, count in distribution_by_status.items()
        ]
        students_by_category = [
            {
                "category": category,
                "display_name": dict(CATEGORY_CHOICES).get(category, category.capitalize()),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for category, count in distribution_by_category.items()
        ]
        return Response({
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
    
    def get(self, request):
        """
        Скачивание аналитики через API.
        Параметры:
        - type: 'full' - полная аналитика, 'month' - аналитика за месяц
        - month: период в формате YYYY-MM (для type=month)
        - date_from: начало периода YYYY-MM-DD (для произвольного периода)
        - date_to: конец периода YYYY-MM-DD (для произвольного периода)
        """
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
