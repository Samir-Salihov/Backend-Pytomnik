# apps/kanban/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError  # ←←←←← ВОТ ЭТО ОБЯЗАТЕЛЬНО!
from apps.students.models import Student

User = get_user_model()


class KanbanBoard(models.Model):
    id = models.CharField("ID доски", max_length=50, primary_key=True)
    title = models.CharField("Название", max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="kanban_boards")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'kanban'
        verbose_name = "Канбан-доска"
        verbose_name_plural = "Канбан-доски"

    def __str__(self):
        return self.title


class KanbanColumn(models.Model):
    COLUMN_TYPES = [
        ('black', 'Чёрный пояс'),
        ('red', 'Красный пояс'),
        ('yellow', 'Жёлтый пояс'),
        ('green', 'Зелёный пояс'),
        ('hr_call', 'Вызов к HR'),
        ('fired', 'Уволен'),
    ]

    id = models.CharField(max_length=30, primary_key=True, choices=COLUMN_TYPES)
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name="columns")
    title = models.CharField("Название колонки", max_length=100)
    color = models.CharField("Цвет (HEX)", max_length=7, default="#6B7280")
    position = models.PositiveSmallIntegerField("Позиция")

    class Meta:
        app_label = 'kanban'
        unique_together = ('board', 'position')
        ordering = ['position']
        indexes = [models.Index(fields=['board', 'id'])]

    def __str__(self):
        return f"{self.board.title} → {self.get_id_display()}"


class StudentKanbanCard(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name="kanban_card"
    )
    column = models.ForeignKey(KanbanColumn, on_delete=models.CASCADE, related_name="cards")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'kanban'
        ordering = ['position']
        indexes = [
            models.Index(fields=['column']),
            models.Index(fields=['student']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['student'],
                name='one_card_per_student'
            )
        ]
        verbose_name = "Карточка студента"
        verbose_name_plural = "Карточки студентов"

    def __str__(self):
        return f"{self.student.full_name} → {self.column.get_id_display()}"

    def clean(self):
        # Защита: студент не может быть на двух досках одновременно
        if StudentKanbanCard.objects.exclude(pk=self.pk).filter(
            student=self.student,
            column__board=self.column.board
        ).exists():
            raise ValidationError("Студент уже есть на этой доске!")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)