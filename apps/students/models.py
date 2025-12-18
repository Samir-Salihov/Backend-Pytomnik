# apps/students/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()

# === Выборы (лучше выносить в константы) ===
LEVEL_CHOICES = [
    ('black', 'Чёрный'),
    ('red', 'Красный'),
    ('yellow', 'Жёлтый'),
    ('green', 'Зелёный'),
]

STATUS_CHOICES = [
    ('active', 'Активные'),
    ('fired', 'Уволенные'),
    ('called_hr', 'Вызваны к HR'),
]

CATEGORY_CHOICES = [
    ('college', 'Колледжисты'),
    ('patriot', 'Патриоты'),
    ('alabuga_start', 'Алабуга Старт (колледжисты)'),
    ('alabuga_mulatki', 'Алабуга Старт (мулатки)'),
]


class StudentQuerySet(models.QuerySet):
    """Оптимизированные запросы"""
    def active(self):
        return self.filter(status='active')

    def by_level(self, level):
        return self.filter(level=level)

    def with_full_name(self):
        return self.annotate(
            full_name=models.F('last_name') + ' ' + models.F('first_name') +
                      models.Coalesce(' ' + models.F('patronymic'), '')
        )


class StudentManager(models.Manager):
    def get_queryset(self):
        return StudentQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def by_level(self, level):
        return self.get_queryset().by_level(level)


class Student(models.Model):
    # Основные данные
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    patronymic = models.CharField("Отчество", max_length=100, blank=True, null=True)

    direction = models.CharField("Направление", max_length=200)
    subdivision = models.CharField("Подразделение", max_length=200, help_text="Где работает/учится")

    age = models.PositiveSmallIntegerField("Возраст")

    # Канбан и статусы
    level = models.CharField("Уровень доступа", max_length=10, choices=LEVEL_CHOICES, default='black')
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='active')
    category = models.CharField("Категория", max_length=30, choices=CATEGORY_CHOICES)

    # Адреса
    address_actual = models.TextField("Фактический адрес проживания")
    address_registered = models.TextField("Адрес по прописке")

    # Контакты
    phone_personal = models.CharField("Личный телефон", max_length=20, unique=True)
    telegram = models.CharField("Telegram (@username)", max_length=100, blank=True, null=True)
    phone_parent = models.CharField("Телефон родителя/представителя", max_length=20)
    fio_parent = models.CharField("Фио родителя/представителя", max_length=200)

    # Медицина
    medical_info = models.TextField("Медицинские данные", blank=True, null=True)


    last_changed_field = models.CharField(
        "Последнее изменённое поле",
        max_length=200,
        blank=True,
        null=True,
        help_text="Автоматически заполняется при смене уровня/статуса"
    )

    # Аудит
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Изменён", auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_students"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="updated_students"
    )

    # Оптимизация
    objects = StudentManager()

    class Meta:
        verbose_name = "Студент (Кот)"
        verbose_name_plural = "Студенты (Коты)"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['phone_personal']),
        ]
        permissions = [
            ("can_change_level", "Может менять уровень доступа"),
            ("can_view_medical_info", "Может видеть мед.данные"),
        ]

    def __str__(self):
        return f"{self.last_name} {self.first_name} | {self.get_level_display()}"

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return " ".join(p for p in parts if p)

    def clean(self):
        if self.age < 14 or self.age > 30:
            raise ValidationError("Возраст должен быть от 14 до 30 лет")

    def save(self, *args, **kwargs):
        # Автозаполнение updated_by при редактировании
        if self.pk and kwargs.get('request'):
            self.updated_by = kwargs.pop('request').user
        super().save(*args, **kwargs)



# в models.py (добавь в конец)

class LevelHistory(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="level_history")
    old_level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    new_level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.student} — {self.get_old_level_display()} → {self.get_new_level_display()}"


class Comment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author} to {self.student}: {self.text[:50]}..."