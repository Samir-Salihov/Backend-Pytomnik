from functools import wraps
from typing import Iterable

from django.core.exceptions import PermissionDenied

try:
    from rest_framework import permissions as drf_permissions
except Exception:
    drf_permissions = None

# Role constants — используйте эти значения в коде проекта
ROLE_MED = "med"
ROLE_ADMIN = "admin"
ROLE_HR_TEV = "hr_tev"
ROLE_HR_CORP = "hr_corp"
ROLE_HR_AC = "hr_ac"

ALL_ROLES = {
    ROLE_MED,
    ROLE_ADMIN,
    ROLE_HR_TEV,
    ROLE_HR_CORP,
    ROLE_HR_AC,
}


def user_has_role(user, *roles: Iterable[str]) -> bool:
    """Проверяет, имеет ли пользователь одну из ролей.

    Суперпользователь (`is_superuser`) — имеет доступ всегда.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "role", None) in set(roles)


def role_required(*roles: Iterable[str]):
    """Декоратор для CBV/FBV, возбуждает PermissionDenied при отсутствии роли."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not user_has_role(request.user, *roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


if drf_permissions:
    class RolePermission(drf_permissions.BasePermission):
        """DRF permission-класс: разрешает доступ пользователям с указанными ролями.

        Для использования: поместите `allowed_roles = ("admin", "hr_tev")` в ваш ViewSet
        или создайте класс-наследник и задайте `allowed_roles`.
        """

        allowed_roles = ()

        def has_permission(self, request, view):
            user = request.user
            if not user or not getattr(user, "is_authenticated", False):
                return False
            if getattr(user, "is_superuser", False):
                return True
            return getattr(user, "role", None) in set(self.allowed_roles)


    def role_permission_factory(roles: Iterable[str]):
        """Возвращает динамический permission класс для заданного набора ролей."""

        class _P(RolePermission):
            allowed_roles = tuple(roles)

        return _P

    # Специализированные permission классы для различных ролей
    
    class AdminOrSuperuserPermission(drf_permissions.BasePermission):
        """Разрешает доступ только Админ-роли или суперпользователю."""
        
        def has_permission(self, request, view):
            user = request.user
            if not getattr(user, "is_authenticated", False):
                return False
            if getattr(user, "is_superuser", False):
                return True
            return getattr(user, "role", None) == ROLE_ADMIN


    class HRTEVOnlyPermission(drf_permissions.BasePermission):
        """Разрешает доступ только HR-ТЕВ и суперпользователю."""
        
        def has_permission(self, request, view):
            user = request.user
            if not getattr(user, "is_authenticated", False):
                return False
            if getattr(user, "is_superuser", False):
                return True
            return getattr(user, "role", None) == ROLE_HR_TEV


    class HRTEVOrAdminPermission(drf_permissions.BasePermission):
        """Разрешает доступ HR-ТЕВ, Админ или суперпользователю."""
        
        def has_permission(self, request, view):
            user = request.user
            if not getattr(user, "is_authenticated", False):
                return False
            if getattr(user, "is_superuser", False):
                return True
            role = getattr(user, "role", None)
            return role in (ROLE_HR_TEV, ROLE_ADMIN)


    class HRCorpOrTEVPermission(drf_permissions.BasePermission):
        """Разрешает доступ HR-Корп.Развитие, HR-ТЕВ или суперпользователю."""
        
        def has_permission(self, request, view):
            user = request.user
            if not getattr(user, "is_authenticated", False):
                return False
            if getattr(user, "is_superuser", False):
                return True
            role = getattr(user, "role", None)
            return role in (ROLE_HR_CORP, ROLE_HR_TEV)


    class HRACOrTEVPermission(drf_permissions.BasePermission):
        """Разрешает доступ HR-AC, HR-ТЕВ или суперпользователю."""
        
        def has_permission(self, request, view):
            user = request.user
            if not getattr(user, "is_authenticated", False):
                return False
            if getattr(user, "is_superuser", False):
                return True
            role = getattr(user, "role", None)
            return role in (ROLE_HR_AC, ROLE_HR_TEV)


    class AllAutheticatedButMedPermission(drf_permissions.BasePermission):
        """Разрешает доступ всем, кроме Медслужбы (и суперпользователю)."""
        
        def has_permission(self, request, view):
            user = request.user
            if not getattr(user, "is_authenticated", False):
                return False
            if getattr(user, "is_superuser", False):
                return True
            role = getattr(user, "role", None)
            return role != ROLE_MED

else:
    # если DRF не установлен — заглушки
    RolePermission = None
    AdminOrSuperuserPermission = None
    HRTEVOnlyPermission = None
    HRTEVOrAdminPermission = None
    HRCorpOrTEVPermission = None
    HRACOrTEVPermission = None
    AllAutheticatedButMedPermission = None

    def role_permission_factory(roles: Iterable[str]):
        return None
