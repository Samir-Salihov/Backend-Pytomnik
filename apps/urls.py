# core/urls.py
from django.contrib import admin
from django.urls import path
from apps.users.views import CustomLoginView, RegisterView, MeView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
]