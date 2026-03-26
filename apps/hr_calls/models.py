from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.students.models import Student
from utils.validators import validate_datetime_not_future

User = get_user_model()

PERSON_TYPE_CHOICES = [
    ('cat', 'Кот'),
    ('not_cat', 'Не кот'),
]

HR_CALL_CATEGORY_CHOICES = [
    ('college', 'Колледжисты'),
    ('alabuga_start_sng', 'АС(СНГ)'),
    ('alabuga_start_rf', 'АС(РФ)'),
    ('alabuga_mulatki', 'АС(МИР)'),
    ('patriot', 'Патриоты'),
]

class HrCall(models.Model):
    person_type = models.CharField(
        "Тип человека",
        max_length=20,
        choices=PERSON_TYPE_CHOICES,
        help_text="Кот или обычный колледжист",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="hr_calls",
        verbose_name="Кот (если есть в базе)"
    )
    category = models.CharField(
        "Категория",
        max_length=50,
        blank=True,
        choices=HR_CALL_CATEGORY_CHOICES,
        help_text="Категория кота (выбирается автоматически по коту)"
    )
    full_name = models.CharField(
        "ФИО",
        max_length=200,
        blank=True,
        help_text="ФИО для колледжиста (обязательно) или авто для кота"
    )
    reason = models.TextField(
        "Причина вызова",
        blank=True,
        help_text="Почему вызван к HR"
    )
    solution = models.TextField(
        "Решение",
        blank=True,
        help_text="Что решили на приёме"
    )
    visit_datetime = models.DateTimeField(
        "Дата и время посещения",
        null=True,
        blank=True,
        help_text="Вручную указывается когда посетил"
    )
    problem_resolved = models.BooleanField(
        "Проблема решена",
        default=False,
        help_text="Если True — статус кота автоматически возвращается на active"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_hr_calls",
        verbose_name="Создал"
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)

    class Meta:
        verbose_name = "Вызов к HR"
        verbose_name_plural = "Вызовы к HR"
        ordering = ['-created_at']

    def __str__(self):
        name = self.full_name if self.person_type == 'not_cat' else (self.student.full_name if self.student else self.full_name or 'Неизвестно')
        return f"Вызов {name} к HR ({self.reason[:50]}...)"

    def clean(self):
        """Комплексная валидация вызова к HR"""
        errors = {}
        
        # Валидация типа лица
        if self.person_type not in ['cat', 'not_cat']:
            errors['person_type'] = "Тип должен быть 'cat' или 'not_cat'"
        
        # Валидация для типа 'cat'
        if self.person_type == 'cat' and not self.student and not (self.full_name and self.full_name.strip()):
            errors['student'] = "Для типа 'cat' укажите кота из базы (student) или заполните ФИО"
        
        # Валидация для типа 'not_cat'
        if self.person_type == 'not_cat' and not (self.full_name and self.full_name.strip()):
            errors['full_name'] = "Для типа 'not_cat' необходимо указать ФИО"
        
        # Валидация ФИО для ручного ввода
        if self.person_type in ('cat', 'not_cat') and self.full_name:
            if len(str(self.full_name).strip()) < 5:
                errors['full_name'] = "ФИО должно содержать минимум 5 символов"
            if len(str(self.full_name)) > 200:
                errors['full_name'] = "ФИО не может быть длиннее 200 символов"
        
        # Валидация дата и время посещения
        if self.visit_datetime:
            try:
                validate_datetime_not_future(self.visit_datetime)
            except ValidationError as e:
                errors['visit_datetime'] = str(e)
        
        # Валидация разница между текущего времени и visit_datetime не более 365 дней
        if self.visit_datetime:
            now = timezone.now()
            min_date = now - timezone.timedelta(days=365)
            if self.visit_datetime < min_date:
                errors['visit_datetime'] = "Дата посещения не может быть раньше чем 1 год назад"
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.person_type == 'cat':
            if self.student:
                self.full_name = self.student.full_name
                # хранится ключ категории (чтобы это было выпадающим списком)
                self.category = self.student.category
        if self.person_type == 'not_cat':
            # для "не кот" категорию не храним
            self.category = ''

        super().save(*args, **kwargs)


class HrComment(models.Model):
    hr_call = models.ForeignKey(
        HrCall,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Вызов"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор"
    )
    text = models.TextField("Текст комментария")
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)
    is_edited = models.BooleanField("Изменено", default=False)

    class Meta:
        verbose_name = "Комментарий к вызову"
        verbose_name_plural = "Комментарии к вызовам"
        ordering = ['-created_at']

    def __str__(self):
        return f"Комментарий от {self.author} к вызову {self.hr_call}"

    def save(self, *args, **kwargs):
        if self.pk:
            self.is_edited = True
        super().save(*args, **kwargs)


class HrFile(models.Model):
    hr_call = models.ForeignKey(
        HrCall,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Вызов"
    )
    # allow very long filenames (container-filesystems like ext4 have high
    # limits, and some clients may generate UUID-based names). default max_length
    # is only 100 which previously caused serializer errors when name exceeded
    # that.  the field itself does not impose size limits on file contents.
    file = models.FileField("Файл", upload_to='hr_calls/files/', max_length=1000)
    description = models.CharField("Описание", max_length=255, blank=True)
    uploaded_at = models.DateTimeField("Загружено", auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Загрузил"
    )

    class Meta:
        verbose_name = "Файл к вызову"
        verbose_name_plural = "Файлы к вызовам"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Файл {self.description or self.file.name} для вызова {self.hr_call}"