from django.contrib import admin
from .models import HrCall, HrComment, HrFile


class HrCommentInline(admin.TabularInline):
    model = HrComment
    extra = 1
    fields = ['author', 'text', 'is_edited']
    readonly_fields = ['created_at', 'updated_at']


class HrFileInline(admin.TabularInline):
    model = HrFile
    extra = 1
    fields = ['file', 'description', 'uploaded_by']
    readonly_fields = ['uploaded_at']


@admin.register(HrCall)
class HrCallAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'get_person_name', 'person_type', 'reason_short', 'solution_short', 
        'visit_datetime', 'problem_resolved', 'created_by', 'created_at', 
    )
    list_filter = ('person_type', 'visit_datetime')
    search_fields = ('full_name', 'student__full_name', 'reason')
    inlines = [HrCommentInline, HrFileInline]
    ordering = ['-created_at']
    readonly_fields = ('created_at', 'updated_at', 'created_by')

    def get_person_name(self, obj):
        if obj.person_type == 'student' and obj.student:
            return obj.student.full_name
        return obj.full_name
    get_person_name.short_description = "ФИО"

    def reason_short(self, obj):
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
    reason_short.short_description = "Причина"

    def solution_short(self, obj):
        return obj.solution[:50] + '...' if len(obj.solution) > 50 else obj.solution
    solution_short.short_description = "Решение"

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj and obj.problem_resolved:
            fields += ('problem_resolved',)  # readonly если решено
        return fields


@admin.register(HrComment)
class HrCommentAdmin(admin.ModelAdmin):
    list_display = ('hr_call', 'author', 'text_short', 'created_at', 'is_edited')
    list_filter = ('hr_call', 'author')
    search_fields = ('text',)
    ordering = ['-created_at']

    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = "Текст"


@admin.register(HrFile)
class HrFileAdmin(admin.ModelAdmin):
    list_display = ('hr_call', 'description', 'file', 'uploaded_by', 'uploaded_at')
    list_filter = ('hr_call', 'uploaded_by')
    search_fields = ('description',)
    ordering = ['-uploaded_at']