from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from django.utils import timezone
from apps.students.models import Student, LevelByMonth


def generate_excel_stream():
    wb = Workbook()
    ws = wb.active
    ws.title = "Колледжисты"

    # Стили
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1E40AF")
    separator_fill = PatternFill("solid", fgColor="3B82F6")  # синий разделитель
    separator_font = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    # Базовые заголовки
    base_headers = [
        "ФИО", "Имя", "Фамилия", "Отчество", "Возраст", "Текущий уровень", "Текущая дата увольнения",
        "Статус", "Категория", "Направление", "Подразделение", "Личный телефон", "Telegram",
        "Телефон родителя", "ФИО родителя", "Адрес фактический", "Адрес по прописке", "Медицинские данные",
        "Создан", "Кем создан", "Изменён"
    ]

    # Заголовки календаря
    months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    calendar_headers = []
    for year in range(2023, 2027):
        for month_name in months_ru:
            calendar_headers.append(f"{month_name} {year}")

    headers = base_headers + calendar_headers

    # Запись заголовков
    for col_num, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    # prepare fills for level coloring
    level_fill_map = {
        'black': PatternFill('solid', fgColor='000000'),
        'yellow': PatternFill('solid', fgColor='FFFF00'),
        'red': PatternFill('solid', fgColor='FF0000'),
        'green': PatternFill('solid', fgColor='00FF00'),
        'fired': PatternFill('solid', fgColor='FFA500'),
        '': PatternFill('solid', fgColor='CCCCCC'),  # no level
        None: PatternFill('solid', fgColor='CCCCCC'),
    }

    # Данные студентов с prefetch
    queryset = Student.objects.select_related('created_by', 'updated_by').prefetch_related('level_by_month').all()

    lbm_dict = {}
    for student in queryset:
        lbm_dict[student.id] = {}
        for lbm in student.level_by_month.all():
            lbm_dict[student.id][(lbm.year, lbm.month)] = lbm

    # Порядок категорий
    category_order = [
        'college', 'alabuga_mulatki', 'alabuga_start_sng', 'patriot', 'alabuga_start_rf'
    ]
    category_names = {
        'college': 'Колледжисты',
        'alabuga_mulatki': 'Алабуга Старт МИР',
        'alabuga_start_sng': 'Алабуга Старт СНГ',
        'patriot': 'Патриоты',
        'alabuga_start_rf': 'Алабуга Старт РФ',
    }

    row_num = 2

    for cat in category_order:
        students_in_cat = [s for s in queryset if s.category == cat]
        students_in_cat.sort(key=lambda s: s.full_name)

        if students_in_cat:
            # Разделитель
            separator_text = f"=== КАТЕГОРИЯ: {category_names.get(cat, cat.upper())} ==="
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=row_num, column=col)
                if col == 1:
                    cell.value = separator_text
                cell.fill = separator_fill
                cell.font = separator_font
                cell.alignment = center
                cell.border = border
            row_num += 1

            # Студенты
            for student in students_in_cat:
                # prepare raw values and track level keys for coloring
                base_values = [
                    student.full_name,
                    student.first_name,
                    student.last_name,
                    student.patronymic or "—",
                    student.age or "—",
                    student.get_level_display(),
                    student.fired_date.strftime('%d.%m.%Y') if student.fired_date else "—",
                    student.get_status_display(),
                    student.get_category_display(),
                    student.get_direction_display() or student.direction or "—",
                    student.get_subdivision_display() or student.subdivision or "—",
                    student.phone_personal,
                    student.telegram or "—",
                    student.phone_parent,
                    student.fio_parent,
                    student.address_actual or "—",
                    student.address_registered or "—",
                    student.medical_info or "—",
                    student.created_at.strftime("%d.%m.%Y %H:%M"),
                    student.created_by.get_full_name() if student.created_by else "—",
                    student.updated_at.strftime("%d.%m.%Y %H:%M"),
                ]
                current_level_key = student.level or ''

                # calendar entries list of (display, level_key)
                calendar_entries = []
                student_lbm = lbm_dict.get(student.id, {})
                for year in range(2023, 2027):
                    for month in range(1, 13):
                        lbm = student_lbm.get((year, month))
                        if lbm and lbm.level:
                            display = lbm.get_level_display()
                            if lbm.level == 'fired' and lbm.fired_date:
                                display += f" ({lbm.fired_date.strftime('%d.%m.%Y')})"
                            calendar_entries.append((display, lbm.level))
                        else:
                            calendar_entries.append(("—", None))

                # write cells one by one so we can color them
                full_values = base_values + [val for val, _ in calendar_entries]
                for col_idx, value in enumerate(full_values, start=1):
                    cell = ws.cell(row=row_num, column=col_idx, value=value)
                    cell.border = border
                    cell.alignment = center

                    # color current level column (index 6)
                    if col_idx == 6:
                        fill = level_fill_map.get(current_level_key, None)
                        if fill:
                            cell.fill = fill
                    # color calendar columns
                    elif col_idx > len(base_headers):
                        cal_idx = col_idx - len(base_headers) - 1
                        level_key = calendar_entries[cal_idx][1]
                        fill = level_fill_map.get(level_key, None)
                        if fill:
                            cell.fill = fill
                row_num += 1

    # Автоширина
    for col_num, column_cells in enumerate(ws.columns, start=1):
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        ws.column_dimensions[get_column_letter(col_num)].width = min(max_length + 4, 60)

    # Заморозка шапки
    ws.freeze_panes = "A2"

    return wb