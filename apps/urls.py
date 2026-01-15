from django.contrib import admin
from django.urls import path, include
from apps.users.views import (
    CustomLoginView,
    RegisterView,
    MeView,
    UserListView,
    UserDetailView,
    ActivateUserView,
    UsersByRoleView,
    ChangePasswordView
)
from rest_framework_simplejwt.views import TokenRefreshView
from apps.students.views import (
    StudentListView, StudentDetailView, StudentCreateView,
    StudentUpdateView, StudentDeleteView, StudentChangeLevelView,
    StudentLevelHistoryView, StudentCommentsView, CommentUpdateView, 
)
from apps.kanban.views import KanbanBoardDetailView, MoveCardView, KanbanBoardCreateView

from apps.export.views import ExportStudentsExcelView

from apps.analytics.views import AnalyticsDashboardView, LevelDistributionView

from apps.analytics.admin import AnalyticsAdmin 


urlpatterns = [
    
    #ручки для польователя
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    #ручки для работы с пользователем
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/activate/', ActivateUserView.as_view(), name='activate-user'),
    path('users/by-role/<str:role>/', UsersByRoleView.as_view(), name='users-by-role'),
    
    #ручки для работы с котами
    path('students/', StudentListView.as_view(), name='student-list'),
    path('students/create/', StudentCreateView.as_view(), name='student-create'),
    path('students/<int:pk>/', StudentDetailView.as_view(), name='student-detail'),
    path('students/<int:pk>/update/', StudentUpdateView.as_view(), name='student-update'),
    path('students/<int:pk>/delete/', StudentDeleteView.as_view(), name='student-delete'),
    path('students/<int:pk>/change-level/', StudentChangeLevelView.as_view(), name='change-level'),
    path('students/<int:pk>/level-history/', StudentLevelHistoryView.as_view(), name='level-history'),
    path('students/<int:pk>/comments/', StudentCommentsView.as_view(), name='student-comments'),
    path('students/<int:student_pk>/comments/<int:comment_pk>/', CommentUpdateView.as_view(), name='comment-update'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('kanban/<str:board_id>/', KanbanBoardDetailView.as_view(), name='board-detail'),  
    path('move/', MoveCardView.as_view(), name='move-card'),
    
    #ручка для экспорта
    path('export/', ExportStudentsExcelView.as_view(), name='export'),
    
    #ручка для аналитики
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('levels/', LevelDistributionView.as_view(), name='level-distribution'),

    path('boards/create/', KanbanBoardCreateView.as_view(), name='kanban-board-create'),
]