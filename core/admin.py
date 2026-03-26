from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect


class CustomAdminSite(admin.AdminSite):
    site_header = 'Pytomnic Admin'
    site_title = 'Pytomnic'
    index_title = 'Admin Panel'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', self.admin_view(self.analytics_redirect), name='analytics-redirect'),
        ]
        return custom_urls + urls
    
    def analytics_redirect(self, request):
        """Редирект на аналитику"""
        return HttpResponseRedirect('/pytomnic-adminka-cats/analytics/analytics/')
    
    def index(self, request, extra_context=None):
        """Добавляем кнопку аналитики на главную страницу админки"""
        extra_context = extra_context or {}
        extra_context['analytics_url'] = reverse('admin:analytics-redirect')
        return super().index(request, extra_context=extra_context)


# Создаем экземпляр кастомной админки
custom_admin_site = CustomAdminSite(name='custom_admin')