from django.urls import path
from .views import AnalyticsDashboardView, LevelDistributionView, analytics_download_view

urlpatterns = [
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('levels/', LevelDistributionView.as_view(), name='level-distribution'),
    path('download/', analytics_download_view, name='analytics-download'),
]