# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "get_full_name",
        "role_badge",
        "status_badge",
        "is_staff",
        "date_joined",
    )
    # Исправлено: убрал role и status_badge из list_editable (нельзя редактировать вычисляемые поля)
    list_editable = ("is_staff",)  # ← можно редактировать только настоящие поля
    list_filter = ("role", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "first_name", "last_name")
    ordering = ("username",)

    # Красивая плашка с ролью
    def role_badge(self, obj):
        colors = {
            "hr": "bg-blue-100 text-blue-800",
            "med": "bg-red-100 text-red-800",
            "saok": "bg-green-100 text-green-800",
            "admin": "bg-purple-100 text-purple-800",
        }
        color = colors.get(obj.role, "bg-gray-100 text-gray-800")
        role_name = {
            "hr": "HR",
            "med": "МЕДСЛУЖБА",
            "saok": "САОК",
            "admin": "АДМИН"
        }.get(obj.role, obj.role.upper())

        return format_html(
            '<span class="px-3 py-1 rounded-full text-xs font-semibold {}">{}</span>',
            color,
            role_name
        )
    role_badge.short_description = "Роль"
    role_badge.admin_order_field = "role"  # ← теперь можно сортировать по роли!

    # Полное имя
    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else "—"
    get_full_name.short_description = "ФИО"

    # Статус активности
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span class="px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">АКТИВЕН</span>'
            )
        return format_html(
            '<span class="px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">ЗАБЛОКИРОВАН</span>'
        )
    status_badge.short_description = "Статус"
    status_badge.admin_order_field = "is_active"  # ← сортировка работает!

    fieldsets = (
        ("Учётные данные", {"fields": ("username", "password")}),
        ("Личная информация", {"fields": ("first_name", "last_name", "role")}),
        ("Права доступа", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",)
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "first_name",
                "last_name",
                "role",
                "password1",
                "password2",
                "is_active",
                "is_staff"
            ),
        }),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Управление пользователями — Питомник Алабуга Старт"
        return super().changelist_view(request, extra_context=extra_context)