from typing import Dict, List, Optional, Any

from rest_framework import serializers

from apps.students.models import Student, LevelHistory


class LevelItemSerializer(serializers.Serializer):
    level = serializers.CharField()
    display_name = serializers.CharField(source='get_level_display', read_only=True)
    count = serializers.IntegerField()
    percentage = serializers.FloatField()
    color = serializers.SerializerMethodField()

    def get_color(self, obj: Dict[str, Any]) -> str:
        colors = {
            'black': '#000000',
            'red': '#ef4444',
            'yellow': '#eab308',
            'green': '#22c55e',
        }
        return colors.get(obj['level'], '#6b7280')


class StatusItemSerializer(serializers.Serializer):
    status = serializers.CharField()
    display_name = serializers.CharField(source='get_status_display', read_only=True)
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class CategoryItemSerializer(serializers.Serializer):
    category = serializers.CharField()
    display_name = serializers.CharField(source='get_category_display', read_only=True)
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class MonthlyGrowthItemSerializer(serializers.Serializer):
    month = serializers.CharField()  # '2025-12'
    added = serializers.IntegerField()
    left = serializers.IntegerField()
    net_growth = serializers.IntegerField()


class TopSubdivisionSerializer(serializers.Serializer):
    subdivision = serializers.CharField(allow_null=True)
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class HRAccountSerializer(serializers.Serializer):
    username = serializers.CharField()
    full_name = serializers.CharField(allow_null=True)
    changes_count = serializers.IntegerField()
    last_change = serializers.DateTimeField(allow_null=True)


class AnalyticsDashboardSerializer(serializers.Serializer):
    total_students = serializers.IntegerField(min_value=0)
    active_students = serializers.IntegerField(min_value=0)
    average_age = serializers.FloatField(allow_null=True)
    students_by_level = LevelItemSerializer(many=True)
    students_by_status = StatusItemSerializer(many=True)
    students_by_category = CategoryItemSerializer(many=True)
    level_changes_last_30_days = serializers.IntegerField(min_value=0)
    students_added_last_30_days = serializers.IntegerField(min_value=0)
    students_left_last_30_days = serializers.IntegerField(min_value=0)
    monthly_growth_last_12_months = MonthlyGrowthItemSerializer(many=True)
    top_5_subdivisions = TopSubdivisionSerializer(many=True)
    top_5_hr_activity_last_30_days = HRAccountSerializer(many=True)
    updated_at = serializers.DateTimeField()