from django.contrib import admin
from django import forms
from django.shortcuts import render
from django.contrib import messages
from django.urls import path
from django.utils.html import format_html, mark_safe
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from .models import Student, LevelHistory, Comment, MedicalFile, LevelByMonth, ViolationAct, CATEGORY_CHOICES
from .forms import PartialDateField
import pandas as pd
from django.urls import reverse
from apps.hr_calls.models import HrCall
from apps.export.services import generate_excel_stream
from decimal import Decimal, InvalidOperation

# we rely on the choice constants and mapping helpers defined in utils
from utils import student_utils


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


def format_fired_date_for_admin(d):
    """Format fired date for admin: day -> dd.mm.yyyy, month -> Russian month + year."""
    if not d:
        return "—"
    # Автоматически определяем точность по дню
    if d.day == 1:
        months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        return f"{months_ru[d.month - 1]} {d.year}"
    return d.strftime('%d.%m.%Y')


class StudentAdminForm(forms.ModelForm):
    fired_date = PartialDateField(
        label='Дата увольнения',
        required=False,
        help_text='Форматы: 01.01.2025 (день), 01.2025 (месяц), Январь 2025 (месяц)'
    )
    
    class Meta:
        model = Student
        fields = '__all__'


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
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
        'direction',
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
            path('delete-all/', self.admin_site.admin_view(self.delete_all_view), name='students_delete_all'),
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
                    updated = 0
                    errors = []

                    # Функция для нормализации строк (удаляет лишние пробелы и приводит к lowercase)
                    def normalize_key(s):
                        if not s:
                            return ''
                        # normalize common Excel header variants (ё/е, multiple spaces, etc.)
                        return ' '.join(str(s).strip().lower().replace('ё', 'е').split())

                    # Robust parsing for dates coming from Excel: strings like 12.12.2000,
                    # actual Excel dates (Timestamp/datetime/date), or Excel serial numbers.
                    def parse_excel_date(val):
                        if val is None or pd.isna(val):
                            return None

                        # pandas/openpyxl often returns Timestamp for date cells
                        if isinstance(val, pd.Timestamp):
                            return val.date()

                        # python datetime/date
                        try:
                            from datetime import datetime, date
                            if isinstance(val, datetime):
                                return val.date()
                            if isinstance(val, date):
                                return val
                        except Exception:
                            pass

                        # Excel serial date number (days since 1899-12-30 in Excel)
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            try:
                                return (pd.Timestamp('1899-12-30') + pd.to_timedelta(float(val), unit='D')).date()
                            except Exception:
                                # fall through to string parsing
                                pass

                        s = str(val).strip()
                        if not s:
                            return None

                        # allow both "." and "," as separators
                        s = s.replace(',', '.')
                        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
                        if pd.isna(dt):
                            raise ValueError(f"Неверная дата: {val!r}. Ожидаю формат вроде 12.12.2000")
                        return dt.date()

                    def parse_fired_date_with_precision(val):
                        """
                        Parse fired date cell value and determine precision:
                        - day: 04.05.2025 (or any excel date)
                        - month: 'Март 2025' / '2025-03' / '03.2025' (no explicit day)
                        Returns: (date|None, precision|None)
                        """
                        if val is None or pd.isna(val):
                            return None, None

                        # excel gives timestamps for real dates
                        if isinstance(val, pd.Timestamp):
                            return val.date(), 'day'

                        try:
                            from datetime import datetime, date
                            if isinstance(val, datetime):
                                return val.date(), 'day'
                            if isinstance(val, date):
                                return val, 'day'
                        except Exception:
                            pass

                        # numeric excel serial => day precision
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            d = parse_excel_date(val)
                            return d, 'day' if d else (None, None)

                        s = str(val).strip()
                        if not s:
                            return None, None

                        s_norm = s.lower().replace('ё', 'е')
                        s_norm = ' '.join(s_norm.split())

                        # year present?
                        import re
                        year_m = re.search(r'(\d{4})', s_norm)
                        if not year_m:
                            d = parse_excel_date(val)
                            return d, 'day' if d else (None, None)
                        year = int(year_m.group(1))

                        # detect month word
                        month_num = None
                        for month_name, month_idx in month_map.items():
                            if month_name in s_norm:
                                month_num = month_idx
                                break

                        # YYYY-MM or YYYY.MM or YYYY/MM
                        m_ym = re.match(r'^\s*(\d{4})[./-](\d{1,2})\s*$', s_norm)
                        if m_ym:
                            m = int(m_ym.group(2))
                            if 1 <= m <= 12:
                                return datetime(year, m, 1).date(), 'month'

                        if month_num:
                            # if the string doesn't explicitly contain a day, treat as month-only
                            # (month-only input like "Март 2025")
                            if re.match(r'^\s*\d{1,2}\s*[.,/-]?\s*\d{1,2}\s*[.,/-]?\s*\d{4}\s*$', s_norm):
                                d = parse_excel_date(val)
                                return d, 'day' if d else (None, None)
                            return datetime(year, month_num, 1).date(), 'month'

                        # fallback: treat as exact date
                        d = parse_excel_date(val)
                        return d, 'day' if d else (None, None)

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

                            # map human-readable strings back to the internal choice keys
                            data = {
                                'first_name': first_name,
                                'last_name': last_name,
                                'patronymic': patronymic,
                                'direction': student_utils.map_choice_value(
                                    safe_str(row.get('Направление')),
                                    student_utils.DIRECTION_CHOICES,
                                ),
                                'subdivision': student_utils.map_choice_value(
                                    safe_str(row.get('Подразделение')),
                                    student_utils.DIVISIONS_CHOICES,
                                ),
                                'category': student_utils.map_choice_value(
                                    safe_str(row.get('Категория', 'college')),
                                    CATEGORY_CHOICES,
                                    default='college'
                                ),
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

                            # Дата рождения (колонка: "Дата рождения", значение: "12.12.2000" и т.п.)
                            birth_raw = row.get('Дата рождения')
                            if pd.notna(birth_raw) and safe_str(birth_raw):
                                data['birth_date'] = parse_excel_date(birth_raw)

                            # Новые поля
                            data['olympiads_participation'] = safe_str(row.get('Участие в олимпиадах')) or None

                            # convert Квазар rank either from key or from display label
                            kvazar = safe_str(row.get('Участие в Квазаре'))
                            if kvazar:
                                data['kvazar_rank'] = student_utils.map_choice_value(
                                    kvazar,
                                    Student.KVAZAR_RANK_CHOICES
                                )
                            else:
                                data['kvazar_rank'] = None

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
                                                        month_data[(year, month)] = {'level': level, 'fired_date': None, 'fired_date_precision': None}

                            for col in df.columns:
                                col_str = str(col).strip()
                                if col_str.startswith('Дата увольнения '):
                                    header = col_str[len('Дата увольнения '):].strip()
                                    parts = header.split()
                                    if len(parts) == 2:
                                        month_name, year_str = parts
                                        month_name_normalized = normalize_key(month_name)
                                        if month_name_normalized in month_map and year_str.isdigit():
                                            year = int(year_str)
                                            month = month_map[month_name_normalized]
                                            key = (year, month)
                                            if key in month_data and month_data[key]['level'] == 'fired':
                                                date_val = row.get(col)
                                                if pd.notna(date_val) and safe_str(date_val):
                                                    try:
                                                        fired_date, fired_precision = parse_fired_date_with_precision(date_val)
                                                        month_data[key]['fired_date'] = fired_date
                                                        month_data[key]['fired_date_precision'] = fired_precision
                                                    except Exception as e:
                                                        errors.append(f"Строка {idx + 2}: Неверная дата в {col}: {e}")

                            # Определяем текущий уровень/статус/дату увольнения
                            now = timezone.now()
                            current_key = (now.year, now.month)

                            # 1) уровень: из колонки "Текущий уровень" если есть, иначе из календаря за текущий месяц
                            current_level_raw = safe_str(row.get('Текущий уровень'))
                            current_level = None
                            if current_level_raw:
                                current_level = level_map.get(normalize_key(current_level_raw))
                            if current_level is None:
                                current_level = month_data.get(current_key, {}).get('level')

                            if current_level is not None:
                                data['level'] = current_level

                            # 2) статус: если уровень уволен -> fired, иначе active
                            # (если в файле есть колонка "Статус" — она может быть человекочитаемой, но
                            # на импорт мы всё равно нормализуем по уровню, чтобы не было рассинхрона)
                            if data.get('level') == 'fired':
                                data['status'] = 'fired'
                            else:
                                data['status'] = 'active'

                            # 3) дата увольнения: при уровне "уволен" берём за текущий месяц, иначе последнюю из month_data
                            fired_items = [
                                v.get('fired_date')
                                for k, v in month_data.items()
                                if v.get('level') == 'fired' and v.get('fired_date')
                            ]
                            fired_date_current = month_data.get(current_key, {}).get('fired_date')

                            if data.get('level') == 'fired':
                                if fired_date_current:
                                    data['fired_date'] = fired_date_current
                                elif fired_items:
                                    d_max = max(fired_items)
                                    data['fired_date'] = d_max
                                else:
                                    data['fired_date'] = None
                            else:
                                data['fired_date'] = None

                            # Всегда создаём нового кота без каких‑либо проверок уникальности
                            # (телефон, ФИО, категория и т.п. могут повторяться)
                            student = Student.objects.create(**data)
                            # Устанавливаем флаг, чтобы не создавать историю уровней для импортированного студента
                            student._is_import = True
                            student.save()
                            created += 1

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

                            if months_imported > 0:
                                messages.info(request, f"Кот {student.full_name}: импортировано {months_imported} месяцев")

                        except Exception as e:
                            errors.append(f"Строка {idx + 2}: {str(e)}")

                    if errors:
                        messages.warning(request, f"Создано {created} котов, обновлено {updated}. Ошибки в {len(errors)} строках.")
                        for error in errors[:20]:
                            messages.warning(request, error)
                    else:
                        messages.success(request, f"Успешно создано {created} котов, обновлено {updated}.")

                    return render(request, "admin/students/import_excel.html", {"form": ExcelImportForm()})

                except Exception as e:
                    messages.error(request, f"Ошибка обработки файла: {str(e)}")
        else:
            form = ExcelImportForm()

        return render(request, "admin/students/import_excel.html", {"form": form})

    def export_excel_view(self, request):
        # support both excel and csv as the public API does
        fmt = request.GET.get('format', 'excel').lower()

        # log the export, using the provided format for traceability
        from apps.export.models import ExportLog
        students_count = Student.objects.count()
        ExportLog.objects.create(user=request.user, format=fmt, students_count=students_count)

        if fmt == 'csv':
            # re-use the same csv export logic as ExportStudentsExcelView
            queryset = Student.objects.select_related('created_by', 'updated_by').prefetch_related('level_by_month').all()

            lbm_dict = {}
            for student in queryset:
                lbm_dict[student.id] = {}
                for lbm in student.level_by_month.all():
                    lbm_dict[student.id][(lbm.year, lbm.month)] = lbm

            months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
            calendar_headers = [f"{m} {y}" for y in range(2023, 2027) for m in months_ru]

            base_headers = [
                "№",
                "ФИО", "Имя", "Фамилия", "Отчество", "Возраст", "Текущий уровень", "Дата увольнения",
                "Статус", "Категория", "Направление", "Подразделение", "Личный телефон", "Telegram",
                "Телефон родителя", "ФИО родителя", "Адрес фактический", "Адрес по прописке",
                "Создан", "Кем создан", "Изменён"
            ]
            headers = base_headers + calendar_headers

            data = []
            category_order = ['college', 'alabuga_mulatki', 'alabuga_start_sng', 'patriot', 'alabuga_start_rf']
            category_names = {
                'college': 'Колледжисты',
                'alabuga_mulatki': 'Алабуга Старт МИР',
                'alabuga_start_sng': 'Алабуга Старт СНГ',
                'patriot': 'Патриоты',
                'alabuga_start_rf': 'Алабуга Старт РФ',
            }

            for cat in category_order:
                students_in_cat = [s for s in queryset if s.category == cat]
                students_in_cat.sort(key=lambda s: s.full_name)
                if students_in_cat:
                    data.append([category_names.get(cat, cat.upper())] + [""] * (len(headers) - 1))
                    counter = 1
                    # последний календарный месяц (для колонки "Дата увольнения")
                    first_this_month = timezone.now().date().replace(day=1)
                    prev_month_end = first_this_month - timezone.timedelta(days=1)
                    prev_month_start = prev_month_end.replace(day=1)
                    for student in students_in_cat:
                        row = [
                            counter,
                            student.full_name,
                            student.first_name,
                            student.last_name,
                            student.patronymic or "—",
                            student.age or "—",
                            student.get_level_display(),
                            format_fired_date_for_admin(student.fired_date)
                            if student.fired_date and prev_month_start <= student.fired_date <= prev_month_end
                            else "—",
                            student.get_status_display(),
                            student.get_category_display(),
                            student.direction or "—",
                            student.subdivision or "—",
                            student.phone_personal,
                            student.telegram or "—",
                            student.phone_parent,
                            student.fio_parent,
                            student.address_actual or "—",
                            student.address_registered or "—",
                            student.created_at.strftime("%d.%m.%Y %H:%M"),
                            student.created_by.get_full_name() if student.created_by else "—",
                            student.updated_at.strftime("%d.%m.%Y %H:%M"),
                        ]
                        student_lbm = lbm_dict.get(student.id, {})
                        for year in range(2023, 2027):
                            for month in range(1, 13):
                                lbm = student_lbm.get((year, month))
                                if lbm and lbm.level:
                                    display = lbm.get_level_display()
                                    if lbm.level == 'fired' and lbm.fired_date:
                                        display += f" ({format_fired_date_for_admin(lbm.fired_date)})"
                                    row.append(display)
                                else:
                                    row.append("—")
                        data.append(row)
                        counter += 1
            df = pd.DataFrame(data, columns=headers)
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response['Content-Disposition'] = f'attachment; filename="export_data_{timezone.now():%Y%m%d_%H%M%S}.csv"'
            df.to_csv(response, index=False, sep=";", encoding="utf-8-sig")
            return response
        # default to excel
        wb = generate_excel_stream()
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        # generic filename without students word to match export API
        response['Content-Disposition'] = f'attachment; filename="export_data_{timezone.now():%Y%m%d_%H%M%S}.xlsx"'
        return response

    def delete_all_view(self, request):
        """Custom admin view to remove all students after confirmation."""
        if request.method == 'POST':
            total = Student.objects.count()
            Student.objects.all().delete()
            self.message_user(request, f"Удалено {total} котов.")
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            return HttpResponseRedirect(reverse('admin:students_student_changelist'))
        # GET: render simple confirmation page
        from django.shortcuts import render
        context = {'title': 'Подтверждение удаления всех котов'}
        return render(request, 'admin/students/delete_all_confirm.html', context)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user

        super().save_model(request, obj, form, change)

    # Полный доступ в админке для роли hr_tev
    def has_view_permission(self, request, obj=None):
        if getattr(request.user, "role", None) == "hr_tev":
            return True
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if getattr(request.user, "role", None) == "hr_tev":
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if getattr(request.user, "role", None) == "hr_tev":
            return True
        return super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        if getattr(request.user, "role", None) == "hr_tev":
            return True
        return super().has_add_permission(request)

    
    def level_calendar_preview(self, obj):
        if not obj.pk:
            return "Сохраните колледжиста для просмотра календаря"

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
                        display += f"<br><small>({format_fired_date_for_admin(lbm.fired_date)})</small>"
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
        return format_fired_date_for_admin(obj.fired_date)
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
            display += f" ({format_fired_date_for_admin(obj.fired_date)})"
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
    student_link.short_description = "Колледжист"

    def month_name(self, obj):
        return timezone.datetime(2000, obj.month, 1).strftime('%B')
    month_name.short_description = "Месяц"

    def level_display(self, obj):
        if obj.level:
            display = obj.get_level_display()
            if obj.level == 'fired' and obj.fired_date:
                display += f" ({format_fired_date_for_admin(obj.fired_date)})"
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
    student_link.short_description = "Колледжист"
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