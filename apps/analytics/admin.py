from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncMonth, ExtractYear
from apps.students.models import Student, LevelHistory
from apps.students.models import Student




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


# Фиктивная модель
class AnalyticsDummy(models.Model):
    class Meta:
        verbose_name = "Аналитика"
        verbose_name_plural = "Аналитика"
        app_label = 'analytics'
        managed = False


@admin.register(AnalyticsDummy)
class AnalyticsAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_staff

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='analytics_dashboard'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        return self.dashboard_view(request)

    def dashboard_view(self, request):
        now = timezone.now()
        today = now.date()
        last_30_days = now - timedelta(days=30)
        last_year_start = now - timedelta(days=365)

        base_qs = Student.objects.select_related('created_by', 'updated_by')

        total = base_qs.count()
        active = base_qs.filter(status='active').count() if total > 0 else 0

        # Средний возраст
        avg_age = base_qs.filter(birth_date__isnull=False).annotate(
            age=ExtractYear(today) - ExtractYear('birth_date')
        ).aggregate(avg_age=Avg('age'))['avg_age']
        avg_age = round(avg_age, 1) if avg_age else None

        # Уровни
        levels = base_qs.values('level').annotate(count=Count('id')).order_by('level')
        level_data = [
            {
                "level": item['level'],
                "display_name": dict(LEVEL_CHOICES).get(item['level'], item['level']),
                "count": item['count'],
                "percentage": round(item['count'] / total * 100, 1) if total > 0 else 0
            }
            for item in levels
        ]

        # Статусы
        statuses = base_qs.values('status').annotate(count=Count('id'))
        status_data = [
            {
                "status": item['status'],
                "display_name": dict(STATUS_CHOICES).get(item['status'], item['status']),
                "count": item['count'],
                "percentage": round(item['count'] / total * 100, 1) if total > 0 else 0
            }
            for item in statuses
        ]

        # Категории
        categories = base_qs.values('category').annotate(count=Count('id'))
        category_data = [
            {
                "category": item['category'],
                "display_name": dict(CATEGORY_CHOICES).get(item['category'], item['category']),
                "count": item['count'],
                "percentage": round(item['count'] / total * 100, 1) if total > 0 else 0
            }
            for item in categories
        ]

        # Динамика 30 дней
        added_30d = base_qs.filter(created_at__gte=last_30_days).count()
        left_30d = base_qs.filter(status='fired', updated_at__gte=last_30_days).count()
        level_changes_30d = LevelHistory.objects.filter(changed_at__gte=last_30_days).count()

        # Топ-5 подразделений (теперь всегда есть, даже если пусто)
        top_subdivisions = (
            base_qs.values('subdivision')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        top_subs = [
            {
                "subdivision": item['subdivision'] or "Не указано",
                "count": item['count'],
                "percentage": round(item['count'] / total * 100, 1) if total > 0 else 0
            }
            for item in top_subdivisions
        ]

        # Динамика по месяцам за год (теперь всегда есть, даже если пусто)
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

        monthly_growth = []
        current = last_year_start
        while current <= now:
            key = current.strftime('%Y-%m')
            added = added_dict.get(key, 0)
            left = left_dict.get(key, 0)
            monthly_growth.append({
                "month": key,
                "added": added,
                "left": left,
                "net_growth": added - left
            })
            current += timedelta(days=30)  # примерно месяц

        data = {
            "total_students": total,
            "active_students": active,
            "average_age": avg_age,
            "students_by_level": level_data,
            "students_by_status": status_data,
            "students_by_category": category_data,
            "level_changes_last_30_days": level_changes_30d,
            "students_added_last_30_days": added_30d,
            "students_left_last_30_days": left_30d,
            "monthly_growth_last_12_months": monthly_growth,
            "top_5_subdivisions": top_subs,
            "updated_at": now,
        }

        # Отладка: выводим данные в админке
        self.message_user(request, f"Данные загружены: всего студентов {total}, уровней {len(level_data)}", level='success')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Аналитический дашборд Питомника',
            'data': data,
            'has_view_permission': True,
        }

        return TemplateResponse(request, 'admin/analytics/dashboard.html', context)