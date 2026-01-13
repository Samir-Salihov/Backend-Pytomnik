from rest_framework import serializers

class LevelDistributionSerializer(serializers.Serializer):
    black  = serializers.IntegerField()
    red    = serializers.IntegerField()
    yellow = serializers.IntegerField()
    green  = serializers.IntegerField()

class StatusDistributionSerializer(serializers.Serializer):
    active   = serializers.IntegerField()
    fired    = serializers.IntegerField()
    called_hr = serializers.IntegerField()

class CategoryDistributionSerializer(serializers.Serializer):
    college        = serializers.IntegerField()
    patriot        = serializers.IntegerField()
    alabuga_start  = serializers.IntegerField()
    alabuga_mulatki = serializers.IntegerField()

class MonthlyGrowthSerializer(serializers.Serializer):
    month = serializers.CharField()  # "2025-12"
    added = serializers.IntegerField()
    left  = serializers.IntegerField()   # уволенные за месяц
    net   = serializers.IntegerField()   # чистый прирост

class AnalyticsDashboardSerializer(serializers.Serializer):
    total_students           = serializers.IntegerField()
    average_age              = serializers.FloatField()
    level_distribution       = LevelDistributionSerializer()
    status_distribution      = StatusDistributionSerializer()
    category_distribution    = CategoryDistributionSerializer()
    level_changes_last_30d   = serializers.IntegerField()
    students_added_last_30d  = serializers.IntegerField()
    students_left_last_30d   = serializers.IntegerField()
    monthly_growth_last_12m  = MonthlyGrowthSerializer(many=True)
    top_5_subdivisions       = serializers.ListField(child=serializers.DictField()) 