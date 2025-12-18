# apps/kanban/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsHRorAdmin(BasePermission):
    """Только HR и админы могут управлять канбаном"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or 
            getattr(request.user, 'role', None) in ['hr', 'admin']
        )


class CanMoveCard(BasePermission):
    """Любой авторизованный может перемещать, но только в рамках правил"""
    def has_permission(self, request, view):
        return request.user.is_authenticated