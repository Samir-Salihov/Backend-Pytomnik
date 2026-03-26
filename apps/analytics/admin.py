from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date
from io import BytesIO

from apps.students.models import Student, CATEGORY_CHOICES
from apps.students.models import LevelHistory
from apps.hr_calls.models import HrCall
from .models import Analytics
from .services import generate_analytics_excel


@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    """Админка для кнопки аналитики"""
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_view_permission(self, request, obj=None):
        return request.user.has_perm('analytics.can_view_analytics')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.analytics_view), name='analytics-dashboard'),
            path('analytics/download/full/', self.admin_site.admin_view(self.download_full), name='analytics-download-full'),
            path('analytics/download/month/', self.admin_site.admin_view(self.download_month), name='analytics-download-month'),
        ]
        return custom_urls + urls
    
    def analytics_view(self, request):
        """Главная страница аналитики"""
        # Основные метрики
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
        
        from django.template.response import TemplateResponse
        context = {
            'total_students': total_students,
            'active_students': active_students,
            'fired_students': fired_students,
            'called_hr_students': called_hr_students,
            'new_students_total': new_students_total,
            'level_changes_total': level_changes_total,
            'distribution_by_level': distribution_by_level,
            'distribution_by_status': distribution_by_status,
            'distribution_by_category': distribution_by_category,
            'last_updated': timezone.now(),
        }
        
        return TemplateResponse(request, 'admin/analytics/dashboard.html', context)
    
    def download_full(self, request):
        """Скачивание полной аналитики"""
        return redirect('analytics-download', type='full')
    
    def download_month(self, request):
        """Скачивание аналитики за месяц"""
        return redirect('analytics-download', type='month')
