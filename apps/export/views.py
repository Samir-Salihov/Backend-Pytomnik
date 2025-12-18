# apps/export/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
from io import BytesIO
from apps.students.models import Student
from .models import ExportLog
from .services import generate_excel_stream

class ExportStudentsExcelView(APIView):
    permission_classes = [IsAuthenticated]

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
            # CSV
            queryset = Student.objects.select_related('created_by', 'updated_by').all()
            data = []
            for s in queryset:
                data.append([
                    s.full_name,
                    s.first_name,
                    s.last_name,
                    s.patronymic or "—",
                    s.age,
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

            import pandas as pd
            df = pd.DataFrame(data, columns=[
                "ФИО", "Имя", "Фамилия", "Отчество", "Возраст", "Уровень", "Статус", "Категория",
                "Направление", "Подразделение", "Личный телефон", "Telegram", "Телефон родителя",
                "ФИО родителя", "Адрес фактический", "Адрес по прописке", "Медицинские данные",
                "Создан", "Кем создан", "Изменён"
            ])

            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response['Content-Disposition'] = f'attachment; filename="pitomnik_students_{timezone.now():%Y%m%d_%H%M%S}.csv"'
            df.to_csv(response, index=False, sep=";", encoding="utf-8-sig")
            return response

        else:
            # EXCEL
            wb = generate_excel_stream()

            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            response = HttpResponse(
                buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ — ЯВНОЕ РАСШИРЕНИЕ И ИМЯ
            response['Content-Disposition'] = f'attachment; filename="pitomnik_students_{timezone.now():%Y%m%d_%H%M%S}.xlsx"; filename*=UTF-8\'\'pitomnik_students_{timezone.now():%Y%m%d_%H%M%S}.xlsx'
            return response