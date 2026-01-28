from django.contrib import admin
from django import forms
from django.shortcuts import render
from django.contrib import messages
from django.urls import path
from django.utils.html import format_html, mark_safe
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from .models import Student, LevelHistory, Comment, MedicalFile, LevelByMonth
import pandas as pd
from django.urls import reverse
from apps.hr_calls.models import HrCall


class MedicalFileInline(admin.TabularInline):
    model = MedicalFile
    extra = 1
    fields = ('file', 'description', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class LevelByMonthInline(admin.TabularInline):
    model = LevelByMonth
    extra = 0
    fields = ('year', 'month', 'level', 'fired_date', 'change_count', 'last_changed_at')
    readonly_fields = ('change_count', 'last_changed_at')
    ordering = ('-year', '-month')
    can_delete = True


class LevelHistoryInline(admin.TabularInline):
    model = LevelHistory
    extra = 0
    fields = ('old_level', 'new_level', 'changed_by', 'changed_at', 'comment')
    readonly_fields = fields
    ordering = ('-changed_at',)
    can_delete = False


class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Выберите файл Excel (.xlsx)",
        widget=forms.FileInput(attrs={'accept': '.xlsx'})
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    inlines = [MedicalFileInline, LevelByMonthInline, LevelHistoryInline]

    list_display = (
        'id',
        'full_name',
        'photo_preview',
        'calculated_age',
        'level_badge',
        'status_badge',
        'hr_status_badge',
        'category',
        'subdivision',
        'fio_parent',
        'created_by_display',
        'updated_by_display',
        'created_at',
        'updated_at',
        'fired_date_preview',
    )
    list_filter = ('level', 'status', 'is_called_to_hr', 'category', 'subdivision', 'created_by', 'updated_by', 'fired_date')
    search_fields = ('last_name', 'first_name', 'patronymic', 'phone_personal', 'telegram', 'fio_parent')
    ordering = ('-updated_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'last_changed_field', 'calculated_age', 'photo_preview', 'level_calendar_preview'
    )

    fieldsets = (
        ('Личная информация', {
            'fields': ('first_name', 'last_name', 'patronymic', 'birth_date', 'calculated_age', 'photo', 'photo_preview')
        }),
        ('Образование и работа', {'fields': ('direction', 'subdivision')}),
        ('Статус и уровень', {'fields': ('level', 'status', 'is_called_to_hr', 'category', 'fired_date')}),
        ('Адреса', {'fields': ('address_actual', 'address_registered')}),
        ('Контакты', {'fields': ('phone_personal', 'telegram', 'phone_parent', 'fio_parent')}),
        ('Медицинские данные', {'fields': ('medical_info',)}),
        ('История уровней (календарь 2023–2026)', {
            'fields': ('level_calendar_preview',),
            'description': mark_safe(
                '<p style="font-size:0.9em; color:#666;">'
                'Визуализация последних уровней по месяцам. '
                'Текущий месяц выделен жёлтым фоном. '
                'Редактируйте уровни в таблице "Level by month" ниже. '
                'Для уровня «Уволен» обязательна дата увольнения. '
                'Наследование «Уволен» на последующие месяцы происходит автоматически.'
                '</p>'
            )
        }),
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

        # Логика вызова к HR через поле is_called_to_hr
        if change:
            old_obj = Student.objects.get(pk=obj.pk)
            if not old_obj.is_called_to_hr and obj.is_called_to_hr:
                from apps.hr_calls.models import HrCall
                if not HrCall.objects.filter(student=obj, person_type='student', problem_resolved=False).exists():
                    HrCall.objects.create(
                        person_type='student',
                        student=obj,
                        reason="",
                        created_by=obj.updated_by
                    )

        super().save_model(request, obj, form, change)

    def level_calendar_preview(self, obj):
        if not obj.pk:
            return "Сохраните студента для просмотра календаря"

        current_year, current_month = timezone.now().year, timezone.now().month

        html = '<div style="font-family: Arial, sans-serif; margin: 20px 0;">'
        html += '<h3 style="text-align: center; margin-bottom: 15px;">История уровней по месяцам (2023–2026)</h3>'
        html += '<table style="width: 100%; border-collapse: collapse; font-size: 0.95em;">'
        html += '<tr>'
        html += '<th style="border: 1px solid #ddd; padding: 10px; background: #f5f5f5; text-align: center;">Год / Месяц</th>'
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        for m in months:
            html += f'<th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: center;">{m}</th>'
        html += '</tr>'

        for year in range(2023, 2027):
            is_current_year = year == current_year
            row_style = 'background: #fffde7;' if is_current_year else ''
            html += f'<tr style="{row_style}">'
            html += f'<td style="border: 1px solid #ddd; padding: 10px; font-weight: bold; text-align: center;">{year}</td>'
            for month in range(1, 13):
                lbm = obj.level_by_month.filter(year=year, month=month).first()
                is_current_month = is_current_year and month == current_month
                cell_style = 'background: #e8f5e8;' if is_current_month else ''
                if lbm and lbm.level:
                    display = lbm.get_level_display()
                    if lbm.level == 'fired' and lbm.fired_date:
                        display += f"<br><small>({lbm.fired_date.strftime('%d.%m.%Y')})</small>"
                    changes = f"<br><small>({lbm.change_count} изм.)</small>" if lbm.change_count > 1 else ""
                    html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; {cell_style}">{display}{changes}</td>'
                else:
                    html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; color: #999; {cell_style}">—</td>'
            html += '</tr>'
        html += '</table>'
        html += '<p style="margin-top: 15px; font-size: 0.9em; color: #666;">'
        html += '• Текущий месяц выделен зелёным фоном.<br>'
        html += '• Текущий год — жёлтым фоном строки.<br>'
        html += '• Редактируйте уровни в таблице "Level by month" ниже.<br>'
        html += '• Для уровня «Уволен» обязательна дата увольнения.<br>'
        html += '• Наследование «Уволен» на последующие месяцы происходит автоматически.'
        html += '</p>'
        html += '</div>'
        return mark_safe(html)
    level_calendar_preview.short_description = "Календарь уровней"

    def fired_date_preview(self, obj):
        if obj.fired_date:
            return obj.fired_date.strftime('%d.%m.%Y')
        return "—"
    fired_date_preview.short_description = "Дата увольнения"

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
        colors = {
            'black': 'bg-dark text-white',
            'red': 'bg-danger text-white',
            'yellow': 'bg-warning text-dark',
            'green': 'bg-success text-white',
            'fired': 'bg-secondary text-white'
        }
        color = colors.get(obj.level, 'bg-secondary text-white')
        display = obj.get_level_display()
        if obj.level == 'fired' and obj.fired_date:
            display += f" ({obj.fired_date.strftime('%d.%m.%Y')})"
        return format_html('<span class="badge {}">{}</span>', color, display)
    level_badge.short_description = "Уровень"

    def status_badge(self, obj):
        colors = {'active': 'bg-primary text-white', 'fired': 'bg-secondary text-white'}
        color = colors.get(obj.status, 'bg-secondary text-white')
        return format_html('<span class="badge {}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = "Статус"

    def hr_status_badge(self, obj):
        if obj.is_called_to_hr:
            return format_html('<span class="badge bg-info text-dark">Вызван к HR</span>')
        return format_html('<span class="badge bg-secondary text-white">Не вызван</span>')
    hr_status_badge.short_description = "Вызов к HR"


@admin.register(LevelByMonth)
class LevelByMonthAdmin(admin.ModelAdmin):
    list_display = ('student_link', 'year', 'month_name', 'level_display', 'fired_date', 'change_count')
    list_filter = ('year', 'month', 'level')
    search_fields = ('student__last_name', 'student__first_name')
    ordering = ('-year', '-month')

    def student_link(self, obj):
        url = reverse("admin:students_student_change", args=[obj.student.id])
        return format_html('<a href="{}">{}</a>', url, obj.student.full_name)
    student_link.short_description = "Студент"

    def month_name(self, obj):
        return timezone.datetime(2000, obj.month, 1).strftime('%B')
    month_name.short_description = "Месяц"

    def level_display(self, obj):
        if obj.level:
            display = obj.get_level_display()
            if obj.level == 'fired' and obj.fired_date:
                display += f" ({obj.fired_date.strftime('%d.%m.%Y')})"
            return display
        return "—"
    level_display.short_description = "Уровень"


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
    search_fields = ('student__first_name', 'student__last_name', 'student__patronymic', 'changed_by__username', 'changed_by__first_name', 'changed_by__last_name')
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


@admin.register(MedicalFile)
class MedicalFileAdmin(admin.ModelAdmin):
    list_display = ('student', 'description', 'file_link', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_by',)
    search_fields = ('description', 'student__first_name', 'student__last_name', 'uploaded_by__username')
    ordering = ('-uploaded_at',)

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Скачать</a>',
                obj.file.url
            )
        return "Нет файла"
    file_link.short_description = "Файл"
    file_link.admin_order_field = 'file'