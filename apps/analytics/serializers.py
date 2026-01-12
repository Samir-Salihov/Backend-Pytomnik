# apps/analytics/serializers.py
from rest_framework import serializers

class AnalyticsDashboardSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    students_by_level = serializers.DictField(child=serializers.IntegerField())
    students_by_status = serializers.DictField(child=serializers.IntegerField())
    students_by_category = serializers.DictField(child=serializers.IntegerField())
    average_age = serializers.FloatField()
    level_changes_last_month = serializers.IntegerField()
    top_subdivisions = serializers.ListField(child=serializers.DictField())

class StudentsByLevelSerializer(serializers.Serializer):
    black = serializers.IntegerField()
    red = serializers.IntegerField()
    yellow = serializers.IntegerField()
    green = serializers.IntegerField()

# Другие сериализаторы для твоих графиков (добавь по аналогии)