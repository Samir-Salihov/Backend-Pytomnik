from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from apps.students.views_admin import bulk_photo_upload

urlpatterns = [
    #Для Admin
    # custom admin views should be declared BEFORE the main admin include
    path('admin/students/bulk-photo-upload/', bulk_photo_upload, name='students_bulk_photo_upload'),
    path('admin/', admin.site.urls),

    #Для Apps
    path('api/v1/', include('apps.urls'), name='apps'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

