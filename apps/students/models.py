from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

LEVEL_CHOICES = [
    ('black', 'Чёрный'),
    ('red', 'Красный'),
    ('yellow', 'Жёлтый'),
    ('green', 'Зелёный'),
    ('fired', 'Уволен'),
]

STATUS_CHOICES = [
    ('active', 'Активные'),
    ('fired', 'Уволенные'),
]

CATEGORY_CHOICES = [
    ('college', 'Колледжисты'),
    ('patriot', 'Патриоты'),
    ('alabuga_start_rf', 'Алабуга Старт (РФ)'),      # ← новая
    ('alabuga_start_sng', 'Алабуга Старт (СНГ)'),
    ('alabuga_mulatki', 'Алабуга Старт (МИР)'),     
]



class StudentQuerySet(models.QuerySet):
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
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    patronymic = models.CharField("Отчество", max_length=100, blank=True, null=True)

    direction = models.CharField("Направление", max_length=200)
    subdivision = models.CharField("Подразделение", max_length=200, help_text="Где работает/учится")

    birth_date = models.DateField("Дата рождения", null=True, blank=True)

    photo = models.ImageField("Фото студента", upload_to='students/photos/', blank=True, null=True)

    level = models.CharField("Уровень доступа", max_length=10, choices=LEVEL_CHOICES, null=True, blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='active')
    category = models.CharField("Категория", max_length=30, choices=CATEGORY_CHOICES)

    address_actual = models.TextField("Фактический адрес проживания")
    address_registered = models.TextField("Адрес по прописке")

    phone_personal = models.CharField("Личный телефон", max_length=20, unique=True)
    telegram = models.CharField("Telegram (@username)", max_length=100, blank=True, null=True)
    phone_parent = models.CharField("Телефон родителя/представителя", max_length=20)
    fio_parent = models.CharField("ФИО родителя/представителя", max_length=200)

    medical_info = models.TextField("Медицинские данные", blank=True, null=True)

    is_called_to_hr = models.BooleanField("Вызван к HR", default=False, help_text="Установите True для вызова к HR")

    last_changed_field = models.CharField(
        "Последнее изменённое поле",
        max_length=200,
        blank=True,
        null=True,
        help_text="Автоматически заполняется при смене уровня/статуса"
    )

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Изменён", auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_students"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="updated_students"
    )

    objects = StudentManager()

    class Meta:
        verbose_name = "Кот"
        verbose_name_plural = "Коты"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.last_name} {self.first_name} | {self.get_level_display()}"

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return " ".join(p for p in parts if p)

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = timezone.now().date()
        delta = relativedelta(today, self.birth_date)
        return delta.years

    def clean(self):
        if self.birth_date:
            age = self.age
            if age is not None and (age < 14 or age > 30):
                raise ValidationError("Возраст должен быть от 14 до 30 лет")

    def save(self, *args, **kwargs):
        if self.pk and kwargs.get('request'):
            self.updated_by = kwargs.pop('request').user

        super().save(*args, **kwargs)


class LevelHistory(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="level_history")
    old_level = models.CharField(max_length=10, choices=LEVEL_CHOICES, null=True, blank=True)
    new_level = models.CharField(max_length=10, choices=LEVEL_CHOICES, null=True, blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = "История изменения уровня"
        verbose_name_plural = "Истории изменений уровней"

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
        verbose_name = "Комментарий к студенту"
        verbose_name_plural = "Комментарии к студентам"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author} to {self.student}: {self.text[:50]}..."


class MedicalFile(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="medical_files")
    file = models.FileField("Медицинский файл", upload_to='students/medical_files/')
    description = models.CharField("Описание", max_length=255, blank=True)
    uploaded_at = models.DateTimeField("Загружен", auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Загрузил"
    )

    class Meta:
        verbose_name = "Медицинский файл"
        verbose_name_plural = "Медицинские файлы"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.description or 'Файл'} для {self.student.full_name}"