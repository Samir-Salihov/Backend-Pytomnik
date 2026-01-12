import django_filters
from apps.students.models import Student, LEVEL_CHOICES, STATUS_CHOICES, CATEGORY_CHOICES

class StudentFilter(django_filters.FilterSet):
    level = django_filters.ChoiceFilter(choices=LEVEL_CHOICES)
    status = django_filters.ChoiceFilter(choices=STATUS_CHOICES)
    category = django_filters.ChoiceFilter(choices=CATEGORY_CHOICES)
    subdivision = django_filters.CharFilter(lookup_expr='icontains')
    direction = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Student
        fields = ['level', 'status', 'category', 'subdivision', 'direction']