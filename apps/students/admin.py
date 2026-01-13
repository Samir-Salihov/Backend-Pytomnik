# apps/students/admin.py
from django.contrib import admin
from django import forms
from django.shortcuts import render
from django.contrib import messages
from django.urls import path
from django.utils.html import format_html
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from .models import Student, LevelHistory, Comment, MedicalFile
import pandas as pd
from django.urls import reverse 

class MedicalFileInline(admin.TabularInline):
    model = MedicalFile
    extra = 1
    fields = ('file', 'description', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Выберите файл Excel (.xlsx)",
        widget=forms.FileInput(attrs={'accept': '.xlsx'})
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    inlines = [MedicalFileInline]

    list_display = (
        'full_name',
        'photo_preview',
        'calculated_age',
        'level_badge',
        'status_badge',
        'category',
        'subdivision',
        'fio_parent',
        'created_by_display',
        'updated_by_display',
        'created_at',
        'updated_at',
    )
    list_filter = ('level', 'status', 'category', 'subdivision', 'created_by', 'updated_by')
    search_fields = ('last_name', 'first_name', 'patronymic', 'phone_personal', 'telegram', 'fio_parent')
    ordering = ('-updated_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'last_changed_field', 'calculated_age', 'photo_preview'
    )

    fieldsets = (
        ('Личная информация', {
            'fields': ('first_name', 'last_name', 'patronymic', 'birth_date', 'calculated_age', 'photo', 'photo_preview')
        }),
        ('Образование и работа', {'fields': ('direction', 'subdivision')}),
        ('Статус и уровень', {'fields': ('level', 'status', 'category')}),
        ('Адреса', {'fields': ('address_actual', 'address_registered')}),
        ('Контакты', {'fields': ('phone_personal', 'telegram', 'phone_parent', 'fio_parent')}),
        ('Медицинские данные', {'fields': ('medical_info',)}),
        ('Метаданные', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by', 'last_changed_field')
        }),
    )

    change_list_template = "admin/students/student_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel_view), name='students_import_excel'),
            path('export-excel/', self.admin_site.admin_view(self.export_excel_view), name='students_export_excel'),
        ]
        return custom_urls + urls

    def import_excel_view(self, request):
        if request.method == "POST":
            form = ExcelImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['excel_file']
                try:
                    df = pd.read_excel(BytesIO(file.read()))
                    created = 0
                    errors = []

                    required = ['Фамилия', 'Имя', 'Личный телефон']
                    missing = [col for col in required if col not in df.columns]
                    if missing:
                        messages.error(request, f"Отсутствуют обязательные колонки: {', '.join(missing)}")
                        return render(request, "admin/students/import_excel.html", {"form": form})

                    for idx, row in df.iterrows():
                        try:
                            data = {
                                'first_name': str(row.get('Имя', '')).strip(),
                                'last_name': str(row.get('Фамилия', '')).strip(),
                                'patronymic': str(row.get('Отчество', '') or '').strip() or None,
                                'direction': str(row.get('Направление', '') or '').strip(),
                                'subdivision': str(row.get('Подразделение', '') or '').strip(),
                                'level': str(row.get('Уровень', 'black') or 'black').lower(),
                                'status': str(row.get('Статус', 'active') or 'active').lower(),
                                'category': str(row.get('Категория', 'college') or 'college').lower(),
                                'address_actual': str(row.get('Адрес фактический', '') or '').strip(),
                                'address_registered': str(row.get('Адрес по прописке', '') or '').strip(),
                                'phone_personal': str(row.get('Личный телефон', '')).strip(),
                                'telegram': str(row.get('Telegram', '') or '').strip() or None,
                                'phone_parent': str(row.get('Телефон родителя', '') or '').strip(),
                                'fio_parent': str(row.get('ФИО родителя', '') or '').strip(),
                                'medical_info': str(row.get('Медицинские данные', '') or '').strip() or None,
                                'created_by': request.user,
                                'updated_by': request.user,
                            }

                            if not data['first_name'] or not data['last_name']:
                                raise ValueError("Имя и фамилия обязательны")
                            if not data['phone_personal']:
                                raise ValueError("Личный телефон обязателен")
                            if Student.objects.filter(phone_personal=data['phone_personal']).exists():
                                raise ValueError(f"Телефон {data['phone_personal']} уже используется")

                            Student.objects.create(**data)
                            created += 1

                        except Exception as e:
                            errors.append(f"Строка {idx + 2}: {str(e)}")

                    if errors:
                        messages.warning(request, f"Создано {created} котов. Ошибки в {len(errors)} строках.")
                        for error in errors[:10]:
                            messages.warning(request, error)
                    else:
                        messages.success(request, f"Успешно создано {created} котов!")

                    return render(request, "admin/students/import_excel.html", {"form": ExcelImportForm()})

                except Exception as e:
                    messages.error(request, f"Ошибка обработки файла: {str(e)}")
        else:
            form = ExcelImportForm()

        return render(request, "admin/students/import_excel.html", {"form": form})

    def export_excel_view(self, request):
        queryset = Student.objects.select_related('created_by', 'updated_by').all()
        data = []
        for s in queryset:
            data.append([
                s.full_name,
                s.first_name,
                s.last_name,
                s.patronymic or "—",
                s.age or "—",
                s.get_level_display(),
                s.get_status_display(),
                s.get_category_display(),
                s.direction or "—",
                s.subdivision or "—",
                s.phone_personal,
                s.telegram or "—",
                s.phone_parent,
                s.fio_parent,
                s.address_actual or "—",
                s.address_registered or "—",
                s.medical_info or "—",
                s.created_at.strftime("%d.%m.%Y %H:%M"),
                s.created_by.get_full_name() if s.created_by else "—",
                s.updated_at.strftime("%d.%m.%Y %H:%M"),
            ])

        df = pd.DataFrame(data, columns=[
            "ФИО", "Имя", "Фамилия", "Отчество", "Возраст", "Уровень", "Статус", "Категория",
            "Направление", "Подразделение", "Личный телефон", "Telegram", "Телефон родителя",
            "ФИО родителя", "Адрес фактический", "Адрес по прописке", "Медицинские данные",
            "Создан", "Кем создан", "Изменён"
        ])

        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"pitomnik_students_{timezone.now():%Y%m%d_%H%M%S}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def calculated_age(self, obj):
        if obj.birth_date:
            return obj.age
        return "—"
    calculated_age.short_description = "Возраст"

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 150px; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.photo.url
            )
        return "(Нет фото)"
    photo_preview.short_description = "Фото"

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = "ФИО"

    def created_by_display(self, obj):
        if obj.created_by:
            return format_html('<b style="color:#10b981;">{}</b>', obj.created_by.get_full_name() or obj.created_by.username)
        return "—"
    created_by_display.short_description = "Кем создан"

    def updated_by_display(self, obj):
        if obj.updated_by:
            return format_html('<b style="color:#f59e0b;">{}</b>', obj.updated_by.get_full_name() or obj.updated_by.username)
        return "—"
    updated_by_display.short_description = "Кем изменён"

    def level_badge(self, obj):
        colors = {'black': 'bg-dark text-white', 'red': 'bg-danger text-white', 'yellow': 'bg-warning text-dark', 'green': 'bg-success text-white'}
        color = colors.get(obj.level, 'bg-secondary text-white')
        return format_html('<span class="badge {}">{}</span>', color, obj.get_level_display())
    level_badge.short_description = "Уровень"

    def status_badge(self, obj):
        colors = {'active': 'bg-primary text-white', 'fired': 'bg-secondary text-white', 'called_hr': 'bg-info text-dark'}
        color = colors.get(obj.status, 'bg-secondary text-white')
        return format_html('<span class="badge {}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = "Статус"


@admin.register(LevelHistory)
class LevelHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'student_link',
        'old_level_display',
        'new_level_display',
        'changed_by_display',
        'changed_at',
        'comment_short'
    )
    list_filter = ('old_level', 'new_level', 'changed_by')
    search_fields = (
        'student__first_name',
        'student__last_name',
        'student__patronymic',
        'changed_by__username',
        'changed_by__first_name',
        'changed_by__last_name'
    )
    ordering = ('-changed_at',)
    readonly_fields = (
        'student',
        'old_level',
        'new_level',
        'changed_by',
        'changed_at',
        'comment'
    )
    date_hierarchy = 'changed_at'

    def student_link(self, obj):
        url = reverse("admin:students_student_change", args=[obj.student.id])
        return format_html(
            '<a href="{}" style="color:#1d4ed8; font-weight:600;">{}</a>',
            url, obj.student.full_name
        )
    student_link.short_description = "Студент"
    student_link.admin_order_field = 'student'

    def old_level_display(self, obj):
        return obj.get_old_level_display()
    old_level_display.short_description = "Старый уровень"
    old_level_display.admin_order_field = 'old_level'

    def new_level_display(self, obj):
        return obj.get_new_level_display()
    new_level_display.short_description = "Новый уровень"
    new_level_display.admin_order_field = 'new_level'

    def changed_by_display(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return "—"
    changed_by_display.short_description = "Кем изменено"
    changed_by_display.admin_order_field = 'changed_by'

    def comment_short(self, obj):
        if obj.comment:
            return obj.comment[:60] + "..." if len(obj.comment) > 60 else obj.comment
        return "—"
    comment_short.short_description = "Комментарий"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('student', 'author', 'text_preview', 'created_at', 'updated_at', 'is_edited')
    list_filter = ('is_edited', 'author')
    search_fields = ('text', 'student__first_name', 'student__last_name', 'author__username')
    ordering = ('-created_at',)

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Комментарий"