from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from apps.students.models import Student
from utils.permissions import HRTEVOrAdminPermission
from .models import ExportLog
from .services import generate_excel_stream
import pandas as pd


class ExportStudentsExcelView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def get(self, request):
        fmt = request.query_params.get("format", "excel").lower()
        user = request.user

        students_count = Student.objects.count()

        ExportLog.objects.create(
            user=user,
            format=fmt,
            students_count=students_count
        )

        if fmt == "csv":
            # CSV — с календарём и разделителями текстом
            queryset = Student.objects.select_related('created_by', 'updated_by').prefetch_related('level_by_month').all()

            lbm_dict = {}
            for student in queryset:
                lbm_dict[student.id] = {}
                for lbm in student.level_by_month.all():
                    lbm_dict[student.id][(lbm.year, lbm.month)] = lbm

            months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
            calendar_headers = [f"{m} {y}" for y in range(2023, 2027) for m in months_ru]

            base_headers = [
                "ФИО", "Имя", "Фамилия", "Отчество", "Возраст", "Текущий уровень", "Текущая дата увольнения",
                "Статус", "Категория", "Направление", "Подразделение", "Личный телефон", "Telegram",
                "Телефон родителя", "ФИО родителя", "Адрес фактический", "Адрес по прописке", "Медицинские данные",
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
                    data.append([f"=== КАТЕГОРИЯ: {category_names.get(cat, cat.upper())} ==="] + [""] * (len(headers) - 1))

                    for student in students_in_cat:
                        row = [
                            student.full_name,
                            student.first_name,
                            student.last_name,
                            student.patronymic or "—",
                            student.age or "—",
                            student.get_level_display(),
                            student.fired_date.strftime('%d.%m.%Y') if student.fired_date else "—",
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
                        ]

                        student_lbm = lbm_dict.get(student.id, {})
                        for year in range(2023, 2027):
                            for month in range(1, 13):
                                lbm = student_lbm.get((year, month))
                                if lbm and lbm.level:
                                    display = lbm.get_level_display()
                                    if lbm.level == 'fired' and lbm.fired_date:
                                        display += f" ({lbm.fired_date.strftime('%d.%m.%Y')})"
                                    row.append(display)
                                else:
                                    row.append("—")

                        data.append(row)

            df = pd.DataFrame(data, columns=headers)

            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response['Content-Disposition'] = f'attachment; filename="pitomnik_students_{timezone.now():%Y%m%d_%H%M%S}.csv"'
            df.to_csv(response, index=False, sep=";", encoding="utf-8-sig")
            return response

        else:
            # Excel — полный с стилями
            wb = generate_excel_stream()

            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            response = HttpResponse(
                buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response['Content-Disposition'] = f'attachment; filename="pitomnik_students_full_{timezone.now():%Y%m%d_%H%M%S}.xlsx"'
            return response