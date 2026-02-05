# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import update_session_auth_hash
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django import forms
from django.core.exceptions import ValidationError
import logging
from .models import User

logger = logging.getLogger(__name__)


class UserCreationForm(forms.ModelForm):
    """Форма для создания пользователя с проверкой паролей"""
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email', 'telegram', 'first_name', 'last_name', 'surname', 'role', 'position')

    def clean_password2(self):
        # Проверка совпадения паролей
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Пароли не совпадают")
        return password2

    def save(self, commit=True):
        # Сохранение пользователя с установкой пароля
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Форма для редактирования пользователя"""
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        required=False,
        help_text="Оставьте пустым, если не хотите менять пароль"
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'telegram', 'first_name', 'last_name', 
            'surname', 'role', 'position', 'bio', 'avatar', 'is_active', 
            'is_staff', 'is_superuser', 'groups', 'user_permissions'
        )

    def save(self, commit=True):
        # Получаем пользователя из БД ДО любых изменений (если это редактирование)
        if self.instance.pk:
            db_user = User.objects.get(pk=self.instance.pk)
            original_password = db_user.password
        else:
            original_password = None
        
        # Используем стандартный super().save() но с commit=False
        user = super().save(commit=False)
        
        # Обновляем пароль только если он был введён
        password_input = self.cleaned_data.get('password')
        if password_input and password_input.strip():  # Проверяем что это не пустая строка
            user.set_password(password_input)
        elif original_password:
            # Если пароль не введён, восстанавливаем оригинальный из БД
            user.password = original_password
        
        if commit:
            user.save()
            # Логирование изменения пароля
            try:
                if original_password and original_password != user.password:
                    logger.info(f"User(id={user.pk}, username={user.username}) password changed in admin.")
            except Exception:
                pass
        
        return user

    def save_m2m(self):
        """Сохраняем M2M поля - вызывается автоматически django.admin при save_related."""
        super().save_m2m()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    
    list_display = (
        "username",
        "get_full_name",
        "email_display",
        "telegram_display",
        "role_badge",
        "position_display",
        "status_badge",
        "is_staff",
        "date_joined_short",
    )
    
    list_editable = ("is_staff",)
    list_filter = ("role", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name", "telegram", "position")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "avatar_preview")
    actions = ["activate_users", "deactivate_users"]
    
    # Поля для отображения в детальном просмотре
    fieldsets = (
        (_("Учётные данные"), {
            "fields": ("username", "password", "email", "telegram")
        }),
        (_("Личная информация"), {
            "fields": ("first_name", "last_name", "surname", "position", "bio")
        }),
        (_("Профессиональная информация"), {
            "fields": ("role", "is_active", "is_staff", "date_joined", "last_login")
        }),
        (_("Аватар"), {
            "fields": ("avatar", "avatar_preview"),
            "classes": ("collapse",)
        }),
        (_("Права доступа"), {
            "fields": ("is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
            "description": _("Расширенные настройки прав доступа")
        }),
    )
    
    # Поля для создания пользователя
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "telegram",
                "first_name",
                "last_name",
                "surname",
                "role",
                "position",
                "bio",
                "password1",
                "password2",
                "is_active",
                "is_staff",
            ),
        }),
    )
    
    # Фильтры по ролям (быстрые фильтры)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Если пользователь не суперпользователь, показываем только активных
        if not request.user.is_superuser:
            qs = qs.filter(is_active=True)
        return qs
    
    # Красивая плашка с ролью
    def role_badge(self, obj):
        colors = {
            "hr": "blue",
            "med": "red",
            "saok": "green",
            "admin": "purple",
        }
        color = colors.get(obj.role, "gray")
        role_name = {
            "hr": "HR",
            "med": "МЕДСЛУЖБА",
            "saok": "САОК",
            "admin": "АДМИН"
        }.get(obj.role, obj.role.upper())

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            role_name
        )
    role_badge.short_description = "Роль"
    role_badge.admin_order_field = "role"
    
    # Полное имя
    def get_full_name(self, obj):
        name_parts = []
        if obj.last_name:
            name_parts.append(obj.last_name)
        if obj.first_name:
            name_parts.append(obj.first_name)
        if obj.surname:
            name_parts.append(obj.surname)
        
        if name_parts:
            return ' '.join(name_parts)
        return format_html('<span style="color: #999;">— не указано —</span>')
    get_full_name.short_description = "ФИО"
    get_full_name.admin_order_field = "last_name"
    
    # Email с иконкой
    def email_display(self, obj):
        if obj.email:
            return format_html(
                '<a href="mailto:{}" style="color: #1a73e8; text-decoration: none;">'
                '📧 {}'
                '</a>',
                obj.email,
                obj.email
            )
        return format_html('<span style="color: #999;">—</span>')
    email_display.short_description = "Email"
    email_display.admin_order_field = "email"
    
    # Telegram с иконкой и ссылкой
    def telegram_display(self, obj):
        if obj.telegram:
            return format_html(
                '<a href="https://t.me/{}" target="_blank" style="color: #1a73e8; text-decoration: none;">'
                '✈️ @{}'
                '</a>',
                obj.telegram,
                obj.telegram
            )
        return format_html('<span style="color: #999;">—</span>')
    telegram_display.short_description = "Telegram"
    telegram_display.admin_order_field = "telegram"
    
    # Должность
    def position_display(self, obj):
        if obj.position:
            return format_html(
                '<span style="background-color: #000; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
                obj.position[:30] + "..." if len(obj.position) > 30 else obj.position
            )
        return format_html('<span style="color: #999;">—</span>')
    position_display.short_description = "Должность"
    position_display.admin_order_field = "position"
    
    # Статус активности
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #d1fae5; color: #065f46; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold; border: 1px solid #a7f3d0;">'
                '✅ АКТИВЕН'
                '</span>'
            )
        return format_html(
            '<span style="background-color: #fee2e2; color: #991b1b; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold; border: 1px solid #fecaca;">'
            '❌ ЗАБЛОКИРОВАН'
            '</span>'
        )
    status_badge.short_description = "Статус"
    status_badge.admin_order_field = "is_active"
    
    # Дата регистрации в коротком формате
    def date_joined_short(self, obj):
        if obj.date_joined:
            return obj.date_joined.strftime("%d.%m.%Y")
        return format_html('<span style="color: #999;">—</span>')
    date_joined_short.short_description = "Регистрация"
    date_joined_short.admin_order_field = "date_joined"
    
    # Превью аватарки
    def avatar_preview(self, obj):
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px; border-radius: 8px; border: 1px solid #ddd;" />',
                obj.avatar.url
            )
        return format_html(
            '<div style="width: 150px; height: 150px; background: #f0f0f0; border-radius: 8px; '
            'display: flex; align-items: center; justify-content: center; color: #999; border: 1px dashed #ccc;">'
            'Нет аватарки'
            '</div>'
        )
    avatar_preview.short_description = "Превью аватарки"
    
    # Действия для массового управления
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано пользователей: {updated}")
    activate_users.short_description = "Активировать выбранных пользователей"
    
    def deactivate_users(self, request, queryset):
        # Не позволяем деактивировать себя
        if request.user in queryset:
            self.message_user(request, "Вы не можете деактивировать себя!", level='error')
            queryset = queryset.exclude(id=request.user.id)
        
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано пользователей: {updated}")
    deactivate_users.short_description = "Деактивировать выбранных пользователей"
    
    # Настройка заголовка
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Управление пользователями — Питомник Алабуга Старт"
        
        return super().changelist_view(request, extra_context=extra_context)
    
    # Настройка формы редактирования
    def get_form(self, request, obj=None, **kwargs):
        """Используем разные формы для создания и редактирования"""
        if obj is None:
            # Для создания нового пользователя
            kwargs['form'] = self.add_form
        else:
            # Для редактирования существующего
            kwargs['form'] = self.form
        
        return super().get_form(request, obj, **kwargs)
    
    # Сохранение пользователя
    def save_model(self, request, obj, form, change):
        """Сохранение пользователя"""
        if not change:
            # Создание нового пользователя - UserCreationForm обработает всё
            form.save()
        else:
            # Редактирование - UserChangeForm обработает пароль и m2m
            form.save()
            
            # Обновляем сессию если администратор менял свой пароль
            if bool(form.cleaned_data.get('password')) and request.user.pk == form.instance.pk:
                update_session_auth_hash(request, form.instance)