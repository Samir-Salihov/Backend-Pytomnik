from rest_framework import serializers
from .models import Student


class StudentShortSerializer(serializers.ModelSerializer):
    """Короткий сериализатор студента для списков по метрикам"""
    full_name = serializers.SerializerMethodField(read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'patronymic', 'full_name',
            'level', 'level_display',
            'status', 'status_display',
            'category', 'category_display',
            'is_called_to_hr'
        ]

    def get_full_name(self, obj):
        return obj.full_name