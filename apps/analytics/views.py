from typing import Dict, Any, List
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Q, Avg, ExpressionWrapper, IntegerField, F, Max
from django.db.models.functions import TruncMonth, ExtractYear
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.students.models import Student, LevelHistory
from apps.users.models import User  
from .serializers import AnalyticsDashboardSerializer

CACHE_TTL = 900  # 15 минут


LEVEL_CHOICES = [
    ('black', 'Чёрный'),
    ('red', 'Красный'),
    ('yellow', 'Жёлтый'),
    ('green', 'Зелёный'),
]

STATUS_CHOICES = [
    ('active', 'Активные'),
    ('fired', 'Уволенные'),
    ('called_hr', 'Вызваны к HR'),
]

CATEGORY_CHOICES = [
    ('college', 'Колледжисты'),
    ('patriot', 'Патриоты'),
    ('alabuga_start', 'Алабуга Старт (СНГ)'),
    ('alabuga_mulatki', 'Алабуга Старт (МИР)'),
]


class AnalyticsDashboardView(APIView):
    """
    Полный аналитический дашборд студентов.
    Кэшируется индивидуально для каждого пользователя на 15 минут.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        cache_key = f"analytics_dashboard_{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        data = self._compute_dashboard()
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)

    def _compute_dashboard(self) -> Dict[str, Any]:
        now = timezone.now()
        today = now.date()
        last_30_days_start = now - timedelta(days=30)
        last_year_start = now - timedelta(days=365)

        # Оптимизированный базовый queryset
        base_qs = Student.objects.select_related('created_by', 'updated_by')

        total_students = base_qs.count()
        if total_students == 0:
            return {"total_students": 0, "message": "Нет данных для анализа"}

        # 1. Общие метрики
        active_count = base_qs.filter(status='active').count()
        fired_count = base_qs.filter(status='fired').count()
        hr_called_count = base_qs.filter(status='called_hr').count()

        # 2. Средний возраст (только у тех, у кого есть birth_date)
        avg_age_qs = base_qs.filter(birth_date__isnull=False).annotate(
            age=ExpressionWrapper(
                ExtractYear(today) - ExtractYear('birth_date'),
                output_field=IntegerField()
            )
        ).aggregate(avg_age=Avg('age'))

        avg_age = round(avg_age_qs['avg_age'], 1) if avg_age_qs['avg_age'] else None

        # 3. Распределение по уровням
        level_qs = (
            base_qs.values('level')
            .annotate(count=Count('id'))
            .order_by('level')
        )
        level_data = [
            {
                "level": item["level"],
                "display_name": dict(LEVEL_CHOICES).get(item["level"], item["level"]),
                "count": item["count"],
                "percentage": round(item["count"] / total_students * 100, 1) if total_students else 0.0
            }
            for item in level_qs
        ]

        # 4. По статусам и категориям
        status_qs = base_qs.values('status').annotate(count=Count('id'))
        status_data = [
            {
                "status": item["status"],
                "display_name": dict(STATUS_CHOICES).get(item["status"], item["status"]),
                "count": item["count"],
                "percentage": round(item["count"] / total_students * 100, 1) if total_students else 0.0
            }
            for item in status_qs
        ]

        category_qs = base_qs.values('category').annotate(count=Count('id'))
        category_data = [
            {
                "category": item["category"],
                "display_name": dict(CATEGORY_CHOICES).get(item["category"], item["category"]),
                "count": item["count"],
                "percentage": round(item["count"] / total_students * 100, 1) if total_students else 0.0
            }
            for item in category_qs
        ]

        # 5. Динамика за последние 30 дней
        added_30d = base_qs.filter(created_at__gte=last_30_days_start).count()
        left_30d = base_qs.filter(status='fired', updated_at__gte=last_30_days_start).count()
        level_changes_30d = LevelHistory.objects.filter(changed_at__gte=last_30_days_start).count()

        # 6. Рост по месяцам (12 месяцев)
        monthly_added = (
            base_qs.filter(created_at__gte=last_year_start)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(added=Count('id'))
            .order_by('month')
        )

        monthly_left = (
            base_qs.filter(status='fired', updated_at__gte=last_year_start)
            .annotate(month=TruncMonth('updated_at'))
            .values('month')
            .annotate(left=Count('id'))
            .order_by('month')
        )

        added_dict = {item['month'].strftime('%Y-%m'): item['added'] for item in monthly_added}
        left_dict = {item['month'].strftime('%Y-%m'): item['left'] for item in monthly_left}

        monthly_growth: List[Dict[str, Any]] = []
        current_month = last_year_start
        while current_month <= now:
            month_key = current_month.strftime('%Y-%m')
            added = added_dict.get(month_key, 0)
            left = left_dict.get(month_key, 0)
            monthly_growth.append({
                "month": month_key,
                "added": added,
                "left": left,
                "net_growth": added - left
            })
            current_month += timedelta(days=30)  # приближение месяца

        # 7. Топ-5 подразделений
        top_subdivisions = (
            base_qs.values('subdivision')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        top_subs = [
            {
                "subdivision": item['subdivision'] or "Не указано",
                "count": item['count'],
                "percentage": round(item['count'] / total_students * 100, 1) if total_students else 0.0
            }
            for item in top_subdivisions
        ]

        # 8. Топ-5 HR по активности за 30 дней
        hr_activity = (
            LevelHistory.objects
            .filter(changed_at__gte=last_30_days_start)
            .values('changed_by__username')
            .annotate(
                changes_count=Count('id'),
                last_change=Max('changed_at')
            )
            .order_by('-changes_count')[:5]
        )
        hr_list = [
            {
                "username": item['changed_by__username'],
                "full_name": User.objects.filter(username=item['changed_by__username']).values_list('last_name', 'first_name', 'surname').first() or (item['changed_by__username'], '', ''),
                "changes_count": item['changes_count'],
                "last_change": item['last_change']
            }
            for item in hr_activity
        ]

        data = {
            "total_students": total_students,
            "active_students": active_count,
            "average_age": avg_age,
            "students_by_level": level_data,
            "students_by_status": status_data,
            "students_by_category": category_data,
            "level_changes_last_30_days": level_changes_30d,
            "students_added_last_30_days": added_30d,
            "students_left_last_30_days": left_30d,
            "monthly_growth_last_12_months": monthly_growth,
            "top_5_subdivisions": top_subs,
            "top_5_hr_activity_last_30_days": hr_list,
            "updated_at": now,
        }

        return data


class LevelDistributionView(APIView):
    """
    Отдельный эндпоинт для распределения по уровням.
    Оптимизирован для быстрого графика.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        cache_key = f"level_distribution_{request.user.id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        total = Student.objects.count()
        if total == 0:
            return Response({"success": True, "data": {"levels": [], "total": 0}})

        qs = (
            Student.objects
            .values('level')
            .annotate(count=Count('id'))
            .order_by('level')
        )

        result = [
            {
                "level": item["level"],
                "display_name": dict(LEVEL_CHOICES).get(item["level"], item["level"]),
                "count": item["count"],
                "percentage": round(item["count"] / total * 100, 1)
            }
            for item in qs
        ]

        data = {"levels": result, "total": total}
        cache.set(cache_key, data, CACHE_TTL)
        return Response({"success": True, "data": data})