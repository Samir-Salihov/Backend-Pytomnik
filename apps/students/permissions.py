# apps/students/permissions.py
from rest_framework.permissions import BasePermission


class IsHRForLevelChange(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'hr'


class CanViewMedicalInfo(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'med'