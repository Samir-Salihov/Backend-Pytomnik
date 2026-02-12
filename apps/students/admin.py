from django.contrib import admin
from django import forms
from django.shortcuts import render
from django.contrib import messages
from django.urls import path
from django.utils.html import format_html, mark_safe
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from .models import Student, LevelHistory, Comment, MedicalFile, LevelByMonth, ViolationAct
import pandas as pd
from django.urls import reverse
from apps.hr_calls.models import HrCall
from decimal import Decimal, InvalidOperation


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


class ViolationActInline(admin.TabularInline):
    model = ViolationAct
    extra = 1
    fields = ('description', 'file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Выберите файл Excel (.xlsx)",
        widget=forms.FileInput(attrs={'accept': '.xlsx'})
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    inlines = [MedicalFileInline, LevelByMonthInline, LevelHistoryInline, ViolationActInline]

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
        ('Дополнительная информация', {  
            'fields': (
                'olympiads_participation',
                'kvazar_rank',
                'rating_place',
                'average_ws',
                'average_mbo',
                'average_di',
            )
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
                    df = pd.read_excel(BytesIO(file.read()), engine='openpyxl')
                    created = 0
                    errors = []

                    # Функция для нормализации строк (удаляет лишние пробелы и приводит к lowercase)
                    def normalize_key(s):
                        if not s:
                            return ''
                        return s.strip().lower()

                    # Маппинги с нормализацией
                    # Жёлтый, Желтый, желтый, жёлтый
                    level_map = {
                        # Чёрный уровень (все варианты)
                        'черный': 'black',
                        'чёрный': 'black',
                        'черный уровень': 'black',
                        'чёрный уровень': 'black',
                        # Красный уровень (все варианты)
                        'красный': 'red',
                        # Жёлтый уровень (все варианты)
                        'желтый': 'yellow',
                        'жёлтый': 'yellow',
                        # Зелёный уровень (все варианты)
                        'зеленый': 'green',
                        'зелёный': 'green',
                        # Уволен (все варианты)
                        'уволен': 'fired',
                        # Без уровня (все варианты)
                        'без уровня': '',
                        'без уровня': '',
                    }
                    kvazar_map = {
                        'сержант': 'sergeant',
                        'рядовой': 'private',
                        'запас': 'reserve',
                    }
                    month_map = {
                        'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4, 'май': 5, 'июнь': 6,
                        'июль': 7, 'август': 8, 'сентябрь': 9, 'октябрь': 10, 'ноябрь': 11, 'декабрь': 12
                    }

                    for idx, row in df.iterrows():
                        try:
                            # Функция безопасного получения строки (убирает NaN → пустая строка)
                            def safe_str(val, default=''):
                                if pd.isna(val):
                                    return default
                                return str(val).strip()

                            # Парсинг ФИО
                            full_name_str = safe_str(row.get('ФИО'))
                            last_name = safe_str(row.get('Фамилия'))
                            first_name = safe_str(row.get('Имя'))
                            patronymic = safe_str(row.get('Отчество')) or None

                            if not last_name or not first_name:
                                if full_name_str:
                                    parts = full_name_str.split()
                                    if len(parts) >= 2:
                                        last_name = parts[0]
                                        first_name = parts[1]
                                        patronymic = parts[2] if len(parts) >= 3 else None
                                    else:
                                        raise ValueError("В колонке ФИО должно быть минимум 2 слова (фамилия + имя)")
                                else:
                                    raise ValueError("Должны быть указаны Фамилия+Имя или колонка ФИО")

                            data = {
                                'first_name': first_name,
                                'last_name': last_name,
                                'patronymic': patronymic,
                                'direction': safe_str(row.get('Направление')),
                                'subdivision': safe_str(row.get('Подразделение')),
                                'category': safe_str(row.get('Категория', 'college')).lower() or 'college',
                                'address_actual': safe_str(row.get('Адрес фактический')),
                                'address_registered': safe_str(row.get('Адрес по прописке')),
                                'phone_personal': safe_str(row.get('Личный телефон')) or None,
                                'telegram': safe_str(row.get('Telegram')) or None,
                                'phone_parent': safe_str(row.get('Телефон родителя')),
                                'fio_parent': safe_str(row.get('ФИО родителя')),
                                'medical_info': safe_str(row.get('Медицинские данные')) or None,
                                'created_by': request.user,
                                'updated_by': request.user,
                            }

                            # Новые поля
                            data['olympiads_participation'] = safe_str(row.get('Участие в олимпиадах')) or None

                            kvazar = safe_str(row.get('Участие в Квазаре'))
                            data['kvazar_rank'] = kvazar_map.get(normalize_key(kvazar)) if kvazar else None

                            rating = row.get('Место в рейтинге')
                            if pd.notna(rating) and safe_str(rating):
                                try:
                                    data['rating_place'] = int(rating)
                                except (ValueError, TypeError):
                                    errors.append(f"Строка {idx + 2}: Неверное место в рейтинге: {rating}")

                            for field, col_name in [
                                ('average_ws', 'Средний WS'),
                                ('average_mbo', 'Средний МБО'),
                                ('average_di', 'Средний ДИ'),
                            ]:
                                val = row.get(col_name)
                                if pd.notna(val) and safe_str(val):
                                    val_str = safe_str(val).replace(',', '.')
                                    try:
                                        data[field] = Decimal(val_str)
                                    except (InvalidOperation, ValueError):
                                        errors.append(f"Строка {idx + 2}: Неверное значение {col_name}: {val}")

                            # Проверка на дубликат телефона (только если указан)
                            if data['phone_personal'] and Student.objects.filter(phone_personal=data['phone_personal']).exists():
                                raise ValueError(f"Телефон {data['phone_personal']} уже используется")

                            # Оставляем level пустым (без уровня по дефолту)
                            data['status'] = 'active'

                            student = Student.objects.create(**data)
                            # Устанавливаем флаг чтобы не создавать История для импортированного студента
                            student._is_import = True
                            student.save()

                            # Календарь (только заполненные)
                            month_data = {}
                            for col in df.columns:
                                col_str = str(col).strip()
                                if col_str.startswith('Уровень '):
                                    header = col_str[len('Уровень '):].strip()
                                    parts = header.split()
                                    if len(parts) == 2:
                                        month_name, year_str = parts
                                        month_name_normalized = normalize_key(month_name)
                                        if month_name_normalized in month_map and year_str.isdigit():
                                            year = int(year_str)
                                            month = month_map[month_name_normalized]
                                            if 2023 <= year <= 2026:
                                                level_display = safe_str(row.get(col))
                                                if level_display:
                                                    level = level_map.get(normalize_key(level_display))
                                                    if level is not None:  # Может быть level='' (Без уровня)
                                                        month_data[(year, month)] = {'level': level, 'fired_date': None}

                            for col in df.columns:
                                col_str = str(col).strip()
                                if col_str.startswith('Дата увольнения '):
                                    header = col_str[len('Дата увольнения '):].strip()
                                    parts = header.split()
                                    if len(parts) == 2:
                                        month_name, year_str = parts
                                        if month_name in month_map and year_str.isdigit():
                                            year = int(year_str)
                                            month = month_map[month_name]
                                            key = (year, month)
                                            if key in month_data and month_data[key]['level'] == 'fired':
                                                date_val = row.get(col)
                                                if pd.notna(date_val) and safe_str(date_val):
                                                    try:
                                                        fired_date = pd.to_datetime(date_val).date()
                                                        month_data[key]['fired_date'] = fired_date
                                                    except Exception as e:
                                                        errors.append(f"Строка {idx + 2}: Неверная дата в {col}: {e}")

                            months_imported = len(month_data)
                            for (year, month), vals in month_data.items():
                                LevelByMonth.objects.update_or_create(
                                    student=student,
                                    year=year,
                                    month=month,
                                    defaults={
                                        'level': vals['level'],
                                        'fired_date': vals['fired_date'],
                                        'last_changed_at': timezone.now(),
                                        'change_count': 1
                                    }
                                )

                            created += 1
                            if months_imported > 0:
                                messages.info(request, f"Кот {student.full_name}: импортировано {months_imported} месяцев")

                        except Exception as e:
                            errors.append(f"Строка {idx + 2}: {str(e)}")

                    if errors:
                        messages.warning(request, f"Создано {created} котов. Ошибки в {len(errors)} строках.")
                        for error in errors[:20]:
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
                if lbm and lbm.level is not None:  # level может быть '' (Без уровня)
                    display = lbm.get_level_display()
                    if lbm.level == 'fired' and lbm.fired_date:
                        display += f"<br><small>({lbm.fired_date.strftime('%d.%m.%Y')})</small>"
                    changes = f"<br><small>({lbm.change_count} изм.)</small>" if lbm.change_count > 1 else ""
                    # Специальный цвет для "Без уровня" (серый фон)
                    cell_bg = 'background: #e5e7eb;' if lbm.level == '' else ''
                    html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; {cell_style} {cell_bg}">{display}{changes}</td>'
                else:
                    html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; color: #999; {cell_style}">—</td>'
            html += '</tr>'
        html += '</table>'
        html += '<p style="margin-top: 15px; font-size: 0.9em; color: #666;">'
        html += '• Текущий месяц выделен зелёным фоном.<br>'
        html += '• Текущий год — жёлтым фоном строки.<br>'
        html += '• Редактируйте уровни в таблице "Level by month" ниже.<br>'
        html += '• Для уровня «Уволен» обязательна дата увольнения.<br>'
        html += '• Наследование «Уволен» на последующие месяцы происходит автоматически.<br>'
        html += '• «Без уровня» отображается серым фоном.'
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
            'fired': 'bg-secondary text-white',
            '': 'bg-gray-500 text-white',
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


@admin.register(ViolationAct)
class ViolationActAdmin(admin.ModelAdmin):
    list_display = ('student', 'description', 'uploaded_at', 'uploaded_by', 'file_link')
    list_filter = ('uploaded_by', 'uploaded_at')
    search_fields = ('description', 'student__last_name', 'student__first_name')
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