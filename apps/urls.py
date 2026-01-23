from django.contrib import admin
from django.urls import path, include
from apps.hr_calls.views import HrCallCreateView, HrCallDetailView, HrCallListView, HrCommentCreateView, HrCommentDetailView, HrCommentListView, HrFileCreateView, HrFileDeleteView, HrFileListView
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
    CommentDeleteView, MedicalFileUploadView, StudentListView, StudentDetailView, StudentCreateView,
    StudentUpdateView, StudentDeleteView, StudentChangeLevelView,
    StudentLevelHistoryView, StudentCommentsView, CommentUpdateView, MedicalFileListView, MedicalFileDeleteView 
)
from apps.kanban.views import KanbanBoardDetailView, MoveCardView, KanbanBoardCreateView

from apps.export.views import ExportStudentsExcelView

from apps.analytics.views import AnalyticsDashboardView, LevelDistributionView

from apps.analytics.admin import AnalyticsAdmin 


urlpatterns = [
    
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/activate/', ActivateUserView.as_view(), name='activate-user'),
    path('users/by-role/<str:role>/', UsersByRoleView.as_view(), name='users-by-role'),
    
    path('students/', StudentListView.as_view(), name='student-list'),
    path('students/create/', StudentCreateView.as_view(), name='student-create'),
    path('students/<int:pk>/', StudentDetailView.as_view(), name='student-detail'),
    path('students/<int:pk>/update/', StudentUpdateView.as_view(), name='student-update'),
    path('students/<int:pk>/delete/', StudentDeleteView.as_view(), name='student-delete'),
    path('students/<int:pk>/change-level/', StudentChangeLevelView.as_view(), name='change-level'),
    path('students/<int:pk>/level-history/', StudentLevelHistoryView.as_view(), name='level-history'),
    path('students/<int:pk>/comments/', StudentCommentsView.as_view(), name='student-comments'),
    path('students/<int:student_pk>/comments/<int:comment_pk>/', CommentUpdateView.as_view(), name='comment-update'),
    path('students/<int:student_pk>/comments/<int:comment_pk>/delete/', CommentDeleteView.as_view(), name='comment-delete'),
    
    path('users/', UserListView.as_view(), name='user-list'),
    path('kanban/<str:board_id>/', KanbanBoardDetailView.as_view(), name='board-detail'),  
    path('move/', MoveCardView.as_view(), name='move-card'),
    
    path('export/', ExportStudentsExcelView.as_view(), name='export'),
    
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('levels/', LevelDistributionView.as_view(), name='level-distribution'),
    path('boards/create/', KanbanBoardCreateView.as_view(), name='kanban-board-create'),

    path('hr-calls/', HrCallListView.as_view(), name='hr_call_list'),
    path('hr-calls/create/', HrCallCreateView.as_view(), name='hr_call_create'),
    path('hr-calls/<int:pk>/', HrCallDetailView.as_view(), name='hr_call_detail'),

    path('hr-calls/<int:pk>/comments/', HrCommentListView.as_view(), name='hr_comment_list'),
    path('hr-calls/<int:pk>/comments/create/', HrCommentCreateView.as_view(), name='hr_comment_create'),
    path('hr-calls/<int:call_pk>/comments/<int:pk>/', HrCommentDetailView.as_view(), name='hr_comment_detail'),

    path('hr-calls/<int:pk>/files/', HrFileListView.as_view(), name='hr_file_list'),
    path('hr-calls/<int:pk>/files/create/', HrFileCreateView.as_view(), name='hr_file_create'),
    path('hr-calls/<int:call_pk>/files/<int:pk>/', HrFileDeleteView.as_view(), name='hr_file_detail'),

    path('students/<int:student_pk>/medical-files/', MedicalFileListView.as_view(), name='medical-file-list'),
    path('students/<int:student_pk>/medical-files/create/', MedicalFileUploadView.as_view(), name='medical-file-create'),
    path('students/<int:student_pk>/medical-files/<int:pk>/delete/', MedicalFileDeleteView.as_view(), name='medical-file-delete'),
]
