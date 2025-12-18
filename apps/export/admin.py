# apps/export/admin.py
from django.contrib import admin
from .models import ExportLog


@admin.register(ExportLog)
class ExportLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'format', 'students_count', 'exported_at')
    list_filter = ('format', 'exported_at', 'user')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('user', 'exported_at', 'format', 'students_count')
    ordering = ('-exported_at',)

    def has_add_permission(self, request):
        return False  # нельзя создавать вручную

    def has_change_permission(self, request, obj=None):
        return False  # нельзя редактировать

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser