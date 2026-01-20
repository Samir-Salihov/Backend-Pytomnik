from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.students.models import Student

User = get_user_model()

PERSON_TYPE_CHOICES = [
    ('student', 'Кот (студент)'),
    ('college', 'Колледжист (не кот)'),
]

class HrCall(models.Model):
    person_type = models.CharField(
        "Тип человека",
        max_length=20,
        choices=PERSON_TYPE_CHOICES,
        help_text="Кот или обычный колледжист"
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="hr_calls",
        verbose_name="Кот (если студент)"
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
        name = self.full_name if self.person_type == 'college' else (self.student.full_name if self.student else 'Неизвестно')
        return f"Вызов {name} к HR ({self.reason[:50]}...)"

    def clean(self):
        if self.person_type == 'student' and not self.student:
            raise ValidationError("Для типа 'student' вызов создаётся автоматически при смене статуса")
        if self.person_type == 'college' and not self.full_name:
            raise ValidationError("Для типа 'college' укажите ФИО")

    def save(self, *args, **kwargs):
        if self.person_type == 'student' and self.student:
            self.full_name = self.student.full_name

        # Если проблема решена — возвращаем статус кота на active
        if self.problem_resolved and self.student and self.student.status == 'called_hr':
            self.student.status = 'active'
            self.student.save(update_fields=['status'])

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
    file = models.FileField("Файл", upload_to='hr_calls/files/')
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