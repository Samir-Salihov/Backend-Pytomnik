# apps/export/services.py
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from django.utils import timezone
from apps.students.models import Student


def generate_excel_stream():
    wb = Workbook()
    ws = wb.active
    ws.title = "Студенты"

    # Заголовки
    headers = [
        "ФИО", "Имя", "Фамилия", "Отчество", "Возраст", "Уровень", "Статус", "Категория",
        "Направление", "Подразделение", "Личный телефон", "Telegram", "Телефон родителя",
        "ФИО родителя", "Адрес фактический", "Адрес по прописке", "Медицинские данные",
        "Создан", "Кем создан", "Изменён"
    ]

    # Стили заголовков
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1E40AF")
    center = Alignment(horizontal="center", vertical="center")
    border = Border(left=Side(style='thin'), right=Side(style='thin'),
                    top=Side(style='thin'), bottom=Side(style='thin'))

    for col_num, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    # Данные — по одному студенту (быстро, без загрузки всей базы)
    row_num = 2
    queryset = Student.objects.select_related('created_by', 'updated_by').iterator(chunk_size=1000)
    for student in queryset:
        ws.append([
            student.full_name,
            student.first_name,
            student.last_name,
            student.patronymic or "—",
            student.age,
            student.get_level_display(),
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
            student.medical_info or "—",
            student.created_at.strftime("%d.%m.%Y %H:%M"),
            student.created_by.get_full_name() if student.created_by else "—",
            student.updated_at.strftime("%d.%m.%Y %H:%M"),
        ])
        row_num += 1

    # Автоширина колонок
    for col_num, column_cells in enumerate(ws.columns, start=1):
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        ws.column_dimensions[get_column_letter(col_num)].width = min(max_length + 4, 50)

    # Заморозка шапки
    ws.freeze_panes = "A2"

    return wb