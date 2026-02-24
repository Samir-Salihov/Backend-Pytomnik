from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging

from utils import student_utils
from utils.validators import (
    validate_birth_date, validate_phone_number, 
    validate_first_name, validate_last_name, validate_patronymic
)
from utils.exceptions import InvalidAgeException, InvalidPhoneException, InvalidNameException


logger = logging.getLogger(__name__)

User = get_user_model()

LEVEL_CHOICES = [
    ('black', 'Чёрный'),
    ('red', 'Красный'),
    ('yellow', 'Жёлтый'),
    ('green', 'Зелёный'),
    ('fired', 'Уволен'),
    ('', 'Без уровня'),
]

STATUS_CHOICES = [
    ('active', 'Активные'),
    ('fired', 'Уволенные'),
]

CATEGORY_CHOICES = [
    ('college', 'Колледжисты'),
    ('patriot', 'Патриоты'),
    ('alabuga_start_rf', 'Алабуга Старт (РФ)'),
    ('alabuga_start_sng', 'Алабуга Старт (СНГ)'),
    ('alabuga_mulatki', 'Алабуга Старт (МИР)'),
]

KVAZAR_RANK_CHOICES = [
    ('sergeant', 'Сержант'),
    ('private', 'Рядовой'),
    ('reserve', 'Запас'),
]

YEARS_CHOICES = [(y, str(y)) for y in range(2023, 2027)]
MONTHS_CHOICES = [(m, str(m)) for m in range(1, 13)]

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

    direction = models.CharField("Направление", max_length=200, choices=student_utils.DIRECTION_CHOICES, blank=True, null=True)
    subdivision = models.CharField("Подразделение", max_length=200, choices=student_utils.DIVISIONS_CHOICES, help_text="Где работает/учится", blank=True, null=True)

    birth_date = models.DateField("Дата рождения", null=True, blank=True)

    # upload_to path remains the same; set a large max_length so
    # filenames of arbitrary length don't trigger database errors.  no
    # additional validators are attached here - the field is intentionally
    # permissive.
    photo = models.ImageField(
        "Фото колледжиста",
        upload_to='students/photos/',
        max_length=1000,
        blank=True,
        null=True,
    )

    level = models.CharField("Уровень доступа", max_length=10, choices=LEVEL_CHOICES, default='', blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='active')
    category = models.CharField("Категория", max_length=30, choices=CATEGORY_CHOICES)

    address_actual = models.TextField("Фактический адрес проживания", blank=True, null=True)
    address_registered = models.TextField("Адрес по прописке", blank=True, null=True)

    phone_personal = models.CharField("Личный телефон", max_length=20, blank=True, null=True)
    telegram = models.CharField("Telegram (@username)", max_length=100, blank=True, null=True)
    phone_parent = models.CharField("Телефон родителя/представителя", max_length=20, blank=True, null=True)
    fio_parent = models.CharField("ФИО родителя/представителя", max_length=200, blank=True, null=True)

    medical_info = models.TextField("Медицинские данные", blank=True, null=True)

    is_called_to_hr = models.BooleanField("Вызван к HR", default=False, help_text="Установите True для вызова к HR")

    fired_date = models.DateField("Дата увольнения", null=True, blank=True)

    last_changed_field = models.CharField(
        "Последнее изменённое поле",
        max_length=200,
        blank=True,
        null=True,
        help_text="Автоматически заполняется при смене уровня/статуса"
    )

    # НОВЫЕ ПОЛЯ
    olympiads_participation = models.TextField("Участие в олимпиадах", blank=True, null=True)
    kvazar_rank = models.CharField("Участие в Квазаре", max_length=20, choices=KVAZAR_RANK_CHOICES, blank=True, null=True)
    rating_place = models.PositiveIntegerField("Место в рейтинге", blank=True, null=True)
    average_ws = models.DecimalField("Средний WS", max_digits=5, decimal_places=2, blank=True, null=True)
    average_mbo = models.DecimalField("Средний МБО", max_digits=5, decimal_places=2, blank=True, null=True)
    average_di = models.DecimalField("Средний ДИ", max_digits=5, decimal_places=2, blank=True, null=True)

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
        """Комплексная валидация данных колледжиста"""
        errors = {}
        
        # Валидат имена
        try:
            if self.first_name:
                validate_first_name(self.first_name)
        except (ValidationError, InvalidNameException) as e:
            errors['first_name'] = str(e)
        
        try:
            if self.last_name:
                validate_last_name(self.last_name)
        except (ValidationError, InvalidNameException) as e:
            errors['last_name'] = str(e)
        
        try:
            if self.patronymic:
                validate_patronymic(self.patronymic)
        except (ValidationError, InvalidNameException) as e:
            errors['patronymic'] = str(e)
        
        # Валидация даты рождения
        try:
            if self.birth_date:
                validate_birth_date(self.birth_date)
        except (ValidationError, InvalidAgeException) as e:
            errors['birth_date'] = str(e)
        
        # Валидация телефонов
        try:
            if self.phone_personal:
                validate_phone_number(self.phone_personal)
        except (ValidationError, InvalidPhoneException) as e:
            errors['phone_personal'] = str(e)
        
        try:
            if self.phone_parent:
                validate_phone_number(self.phone_parent)
        except (ValidationError, InvalidPhoneException) as e:
            errors['phone_parent'] = str(e)
        
        # Валидация даты увольнения
        if self.fired_date and self.level != 'fired':
            errors['fired_date'] = "Дата увольнения может быть указана только для уровня 'Уволен'"
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.pk and kwargs.get('request'):
            self.updated_by = kwargs.pop('request').user
        if self.level == 'fired':
            self.status = 'fired'
        else:
            self.status = 'active'

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

    def get_old_level_display(self):
        """Возвращает отображаемое значение старого уровня, включая 'Без уровня' вместо None"""
        return dict(LEVEL_CHOICES).get(self.old_level, self.old_level or '—')

    def get_new_level_display(self):
        """Возвращает отображаемое значение нового уровня, включая 'Без уровня' вместо None"""
        return dict(LEVEL_CHOICES).get(self.new_level, self.new_level or '—')


class LevelByMonth(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="level_by_month")
    year = models.IntegerField(choices=YEARS_CHOICES)
    month = models.IntegerField(choices=MONTHS_CHOICES)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, null=True, blank=True)
    fired_date = models.DateField(null=True, blank=True)
    last_changed_at = models.DateTimeField(null=True, blank=True)
    change_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('student', 'year', 'month')
        ordering = ['year', 'month']

    def __str__(self):
        return f"{self.student} — {self.year}-{self.month:02d}: {self.level or '—'}"

    def get_level_display(self):
        return dict(LEVEL_CHOICES).get(self.level, self.level or '—')


class Comment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Комментарий к колледжисту"
        verbose_name_plural = "Комментарии к колледжистам"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author} to {self.student}: {self.text[:50]}..."


class MedicalFile(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="medical_files")
    # make room for long filenames; no validators applied
    file = models.FileField(
        "Медицинский файл",
        upload_to='students/medical_files/',
        max_length=1000,
    )
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


class ViolationAct(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="violation_acts")
    description = models.TextField("Описание нарушения/акта")
    # allow very long filenames and optional upload
    file = models.FileField(
        "Файл",
        upload_to='students/violation_acts/',
        max_length=1000,
        blank=True,
        null=True,
    )
    uploaded_at = models.DateTimeField("Загружен", auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Загрузил"
    )

    class Meta:
        verbose_name = "Объяснительная/Акт"
        verbose_name_plural = "Объяснительные и Акты"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.description[:50]}... для {self.student.full_name}"