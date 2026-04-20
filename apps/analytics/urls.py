from django.urls import path
from .views import (
    AnalyticsDashboardView,
    LevelDistributionView,
    LevelDistributionAPView,
    LevelDistributionASPatriotsView,
    QuarterlyAnalyticsView,
    QuarterlyAnalyticsAPView,
    QuarterlyAnalyticsASPatriotsView,
    AnalyticsMetricsStudentsView,
    AnalyticsAPView,
    AnalyticsASPatriotsView,
    analytics_download_view
)

urlpatterns = [
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    
    # Аналитика по уровням
    path('levels/', LevelDistributionView.as_view(), name='level-distribution'),
    path('levels/ap/', LevelDistributionAPView.as_view(), name='level-distribution-ap'),
    path('levels/as-patriots/', LevelDistributionASPatriotsView.as_view(), name='level-distribution-as-patriots'),
    
    # Квартальная аналитика
    path('quarterly/', QuarterlyAnalyticsView.as_view(), name='quarterly-analytics'),
    path('quarterly/ap/', QuarterlyAnalyticsAPView.as_view(), name='quarterly-analytics-ap'),
    path('quarterly/as-patriots/', QuarterlyAnalyticsASPatriotsView.as_view(), name='quarterly-analytics-as-patriots'),
    
    path('download/', analytics_download_view, name='analytics-download'),
    path('metrics/students/', AnalyticsMetricsStudentsView.as_view(), name='analytics-metrics-students'),
    path('college/', AnalyticsAPView.as_view(), name='analytics-college'),
    path('as-patriots/', AnalyticsASPatriotsView.as_view(), name='analytics-as-patriots'),
]
