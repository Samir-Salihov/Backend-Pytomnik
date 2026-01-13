# apps/analytics/views.py
from typing import Dict, List, Any
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.db.models import Count, Avg, F, ExpressionWrapper, FloatField, Q, Case, When, Value, CharField
from django.db.models.functions import TruncMonth
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from apps.students.models import Student, LevelHistory

CACHE_TTL = 900  # 15 минут кэширования


class AnalyticsDashboardView(APIView):
    """
    Основной дашборд аналитики:
    - Общее количество студентов
    - Средний возраст
    - Распределение по уровням / статусам / категориям / возрастным группам
    - Динамика за последние 30 дней (добавлено / уволено / смены уровней)
    - Рост/убыль по месяцам за последний год
    - Топ-5 подразделений
    - Активность HR за 30 дней (кто сколько раз менял уровни)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        cache_key = f"analytics_dashboard_{request.user.id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)

        data = self._compute_full_dashboard()
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data, status=status.HTTP_200_OK)

    def _compute_full_dashboard(self) -> Dict[str, Any]:
        now = timezone.now()
        last_30_days = now - relativedelta(days=30)
        last_year_start = now - relativedelta(years=1)

        # 1. Основные метрики
        total_students = Student.objects.count()

        # Средний возраст — эффективно через базу
        avg_age = Student.objects.filter(birth_date__isnull=False).aggregate(
            avg=ExpressionWrapper(
                now.year - F('birth_date__year') -
                Case(When(birth_date__month__gt=now.month, then=Value(1)), default=Value(0)),
                output_field=FloatField()
            )
        )['avg'] or 0.0

        # 2. Распределения
        level_dist     = self._get_distribution('level')
        status_dist    = self._get_distribution('status')
        category_dist  = self._get_distribution('category')
        age_groups     = self._get_age_groups()

        # 3. Динамика за 30 дней
        level_changes_30d = LevelHistory.objects.filter(changed_at__gte=last_30_days).count()
        added_30d         = Student.objects.filter(created_at__gte=last_30_days).count()
        left_30d          = Student.objects.filter(status='fired', updated_at__gte=last_30_days).count()

        # 4. Рост/убыль по месяцам (12 месяцев)
        monthly_trend = self._get_monthly_trend(last_year_start, now)

        # 5. Топ-5 подразделений
        top_subs = self._get_top_subdivisions()

        # 6. Активность HR за 30 дней
        hr_activity = self._get_hr_activity(last_30_days)

        return {
            "total_students": total_students,
            "average_age": round(avg_age, 1),
            "level_distribution": level_dist,
            "status_distribution": status_dist,
            "category_distribution": category_dist,
            "age_group_distribution": age_groups,
            "level_changes_last_30_days": level_changes_30d,
            "students_added_last_30_days": added_30d,
            "students_left_last_30_days": left_30d,
            "monthly_trend_last_12m": monthly_trend,
            "top_5_subdivisions": top_subs,
            "hr_activity_last_30_days": hr_activity,
        }

    def _get_distribution(self, field: str) -> Dict[str, int]:
        """Возвращает словарь распределения по полю (например level, status, category)"""
        return dict(
            Student.objects.values(field)
                           .annotate(count=Count('id'))
                           .values_list(field, 'count')
        )

    def _get_age_groups(self) -> Dict[str, int]:
        """Распределение студентов по возрастным группам"""
        now = timezone.now()
        groups = Student.objects.filter(birth_date__isnull=False).annotate(
            age_group=Case(
                When(birth_date__year__gte=now.year - 18, then=Value('14–18')),
                When(birth_date__year__gte=now.year - 23, then=Value('19–23')),
                When(birth_date__year__gte=now.year - 30, then=Value('24–30')),
                default=Value('неизвестно'),
                output_field=CharField()
            )
        ).values('age_group').annotate(count=Count('id'))

        return {item['age_group']: item['count'] for item in groups}

    def _get_monthly_trend(self, start_date, end_date) -> List[Dict]:
        """Динамика добавлений и увольнений по месяцам за год"""
        added = (
            Student.objects.filter(created_at__gte=start_date)
                           .annotate(month=TruncMonth('created_at'))
                           .values('month')
                           .annotate(added=Count('id'))
                           .order_by('month')
        )

        left = (
            Student.objects.filter(status='fired', updated_at__gte=start_date)
                           .annotate(month=TruncMonth('updated_at'))
                           .values('month')
                           .annotate(left=Count('id'))
                           .order_by('month')
        )

        added_dict = {m['month'].strftime('%Y-%m'): m['added'] for m in added}
        left_dict  = {m['month'].strftime('%Y-%m'): m['left'] for m in left}

        result = []
        current = start_date
        while current <= end_date:
            month_key = current.strftime('%Y-%m')
            added_count = added_dict.get(month_key, 0)
            left_count  = left_dict.get(month_key, 0)
            result.append({
                "month": month_key,
                "added": added_count,
                "left":  left_count,
                "net":   added_count - left_count
            })
            current += relativedelta(months=1)

        return result

    def _get_top_subdivisions(self, limit: int = 5) -> List[Dict]:
        """Топ-N подразделений по количеству студентов"""
        qs = (
            Student.objects.values('subdivision')
                           .annotate(count=Count('id'))
                           .order_by('-count')[:limit]
        )
        return [
            {"name": item['subdivision'] or "Не указано", "count": item['count']}
            for item in qs
        ]

    def _get_hr_activity(self, since) -> List[Dict]:
        """Активность HR за период (кто сколько раз менял уровни)"""
        qs = (
            LevelHistory.objects.filter(changed_at__gte=since)
                               .values('changed_by__username')
                               .annotate(changes=Count('id'))
                               .order_by('-changes')[:10]
        )
        return [
            {"username": item['changed_by__username'], "changes": item['changes']}
            for item in qs
        ]


class LevelDistributionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        data = Student.objects.values('level').annotate(count=Count('id'))
        return Response(dict(data), status=status.HTTP_200_OK)


class AgeGroupDistributionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        now = timezone.now()
        data = Student.objects.filter(birth_date__isnull=False).annotate(
            age_group=Case(
                When(birth_date__year__gte=now.year - 18, then=Value('14–18')),
                When(birth_date__year__gte=now.year - 23, then=Value('19–23')),
                When(birth_date__year__gte=now.year - 30, then=Value('24–30')),
                default=Value('неизвестно'),
                output_field=CharField()
            )
        ).values('age_group').annotate(count=Count('id'))
        return Response({item['age_group']: item['count'] for item in data}, status=status.HTTP_200_OK)