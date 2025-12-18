# apps/users/models.py
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator, RegexValidator
import os


def user_avatar_upload_path(instance, filename):
    """Генерирует путь для сохранения аватарки пользователя"""
    ext = filename.split('.')[-1]
    filename = f"avatar_{instance.username}_{instance.id}.{ext}"
    return os.path.join('users/avatars/', filename)


class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Логин обязателен")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")
        
            
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # Основные поля
    username = models.CharField(_("Логин"), max_length=50, unique=True)
    email = models.EmailField(
        _("Электронная почта"),
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        validators=[EmailValidator()]
    )
    
    telegram = models.CharField(
        _("Telegram"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Имя пользователя в Telegram (без @)"),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_]{5,32}$',
                message=_("Имя пользователя Telegram должно содержать только латинские буквы, цифры и подчеркивания (5-32 символа)")
            )
        ]
    )
    
    # Личные данные
    first_name = models.CharField(_("Имя"), max_length=100, blank=True)
    last_name = models.CharField(_("Фамилия"), max_length=100, blank=True)
    surname = models.CharField(_("Отчество"), max_length=100, blank=True)
    
    # Профессиональная информация
    role = models.CharField(
        _("Роль"),
        max_length=20,
        choices=[
            ("hr", "HR"),
            ("med", "Медслужба"),
            ("saok", "САОК"),
            ("admin", "Админ")
        ],
        default="hr",
    )
    
    position = models.CharField(
        _("Должность"),
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Официальная должность в организации")
    )
    
    # Биография
    bio = models.TextField(
        _("О себе"),
        max_length=1000,
        blank=True,
        null=True,
        help_text=_("Краткая информация о себе")
    )
    
    # Аватарка
    avatar = models.ImageField(
        _("Аватар"),
        upload_to=user_avatar_upload_path,
        max_length=500,
        blank=True,
        null=True,
        help_text=_("Рекомендуемый размер: 300x300 пикселей")
    )
    
    # Системные поля
    is_active = models.BooleanField(_("Активен"), default=True)
    is_staff = models.BooleanField(_("Сотрудник"), default=False)
    date_joined = models.DateField(
        _("Дата регистрации"),
        auto_now_add=True,
        
    )
    last_login = models.DateTimeField(_("Последний вход"), blank=True, null=True)
    
    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return self.username
    
    def get_full_name(self):
        """Возвращает полное имя в формате 'Фамилия Имя Отчество'"""
        parts = []
        if self.last_name:
            parts.append(self.last_name)
        if self.first_name:
            parts.append(self.first_name)
        if self.surname:
            parts.append(self.surname)
        return ' '.join(parts) if parts else self.username
    
    @property
    def avatar_url(self):
        """Возвращает URL аватарки или дефолтный"""
        if self.avatar:
            return self.avatar.url
        return "/static/images/default_avatar.png"
    
    @property
    def has_avatar(self):
        """Проверяет, есть ли у пользователя аватарка"""
        return bool(self.avatar) and hasattr(self.avatar, 'url')
    
    @property
    def telegram_link(self):
        """Возвращает ссылку на Telegram профиль"""
        if self.telegram:
            return f"https://t.me/{self.telegram}"
        return None
    
    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        
        # Приведение telegram к нижнему регистру
        if self.telegram:
            self.telegram = self.telegram.lower()