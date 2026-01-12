# apps/search/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.students.models import Student, LEVEL_CHOICES, STATUS_CHOICES, CATEGORY_CHOICES
from .filters import StudentFilter
from .documents import StudentDocument

class StudentSearchView(APIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = StudentFilter

    def get(self, request):
        query = request.GET.get('q', '').strip()

        # 1. Применяем фильтры из БД (level, status, category и т.д.)
        queryset = Student.objects.all()
        filtered_qs = self.filterset_class(request.GET, queryset=queryset).qs

        # 2. Если есть текстовый запрос — ищем в Elasticsearch
        if query:
            search = StudentDocument.search().query(
                "multi_match",
                query=query,
                fields=[
                    "full_name^3",
                    "phone_personal^2",
                    "telegram",
                    "subdivision",
                    "direction",
                    "fio_parent",
                ],
                type="bool_prefix",
                fuzziness="AUTO"
            )[:50]  # увеличил лимит

            # Ограничиваем поиск только отфильтрованными студентами
            if filtered_qs.exists():
                student_ids = [str(id) for id in filtered_qs.values_list('id', flat=True)]
                search = search.filter("terms", id=student_ids)

            response = search.execute()
            hit_ids = [hit.meta.id for hit in response.hits]

            # Сохраняем порядок от Elasticsearch (релевантность)
            if hit_ids:
                order_map = {str(hit_id): index for index, hit_id in enumerate(hit_ids)}
                queryset = filtered_qs.filter(id__in=hit_ids)
                queryset = sorted(queryset, key=lambda s: order_map.get(str(s.id), len(order_map)))
            else:
                queryset = []
        else:
            # Если нет текста — просто возвращаем отфильтрованный queryset
            queryset = filtered_qs

        # Формируем ответ
        results = []
        for student in queryset[:50]:
            results.append({
                "id": student.id,
                "full_name": student.full_name,
                "age": student.age,
                "level_display": student.get_level_display(),
                "status_display": student.get_status_display(),
                "category_display": student.get_category_display(),
                "phone_personal": student.phone_personal,
                "telegram": student.telegram or "—",
                "subdivision": student.subdivision,
                "direction": student.direction,
            })

        return Response({
            "query": query,
            "count": len(results),
            "results": results
        })