# apps/users/models.py
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_("Логин"), max_length=50, unique=True)
    first_name = models.CharField(_("Имя"), max_length=100, blank=True)
    last_name = models.CharField(_("Фамилия"), max_length=100, blank=True)
    surname = models.CharField(_("Отчество"), max_length=100, blank=True)
    role = models.CharField(
        _("Роль"),
        max_length=20,
        choices=[("hr", "HR"), ("med", "Медслужба"), ("saok", "САОК"), ("admin", "Админ")],
        default="hr",
    )
    is_active = models.BooleanField(_("Активен"), default=True)
    is_staff = models.BooleanField(_("Сотрудник"), default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username