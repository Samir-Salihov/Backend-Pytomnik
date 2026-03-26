from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from apps.students.views_admin import bulk_photo_upload
from apps.analytics.views import analytics_download_view

urlpatterns = [
    # Для Admin (жёсткий URL, как просил пользователь)
    path('pytomnic-adminka-cats/students/bulk-photo-upload/', bulk_photo_upload, name='students_bulk_photo_upload'),
    path('pytomnic-adminka-cats/', admin.site.urls),

    # Для Apps
    path('api/v1/', include('apps.urls'), name='apps'),

    # Выгрузка аналитики без API
    path('analytics/download/', analytics_download_view, name='analytics-download'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

