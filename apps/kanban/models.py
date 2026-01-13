from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.students.models import Student

User = get_user_model()


class KanbanBoard(models.Model):
    slug = models.SlugField("Slug доски", max_length=50, unique=True)  # polytech, alabuga-start — уникальный глобально
    title = models.CharField("Название", max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="kanban_boards")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Канбан-доска"
        verbose_name_plural = "Канбан-доски"
        ordering = ['slug']

    def __str__(self):
        return self.title

    def get_students(self):
        """Возвращает студентов для этой доски"""
        if self.slug == "polytech":
            return Student.objects.exclude(category__in=['alabuga_start', 'alabuga_mulatki'])
        elif self.slug == "alabuga-start":
            return Student.objects.filter(category__in=['alabuga_start', 'alabuga_mulatki'])
        return Student.objects.none()


class KanbanColumn(models.Model):
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name="columns")
    slug = models.CharField("Slug уровня", max_length=30)  # black, red, yellow, green — задаётся вручную
    title = models.CharField("Название колонки", max_length=100)
    color = models.CharField("Цвет (HEX)", max_length=7, default="#6B7280")
    position = models.PositiveSmallIntegerField("Позиция", default=0)

    class Meta:
        unique_together = ('board', 'slug')  # уникальность только внутри одной доски
        ordering = ['position']
        indexes = [models.Index(fields=['board', 'slug'])]

    def __str__(self):
        return f"{self.board.title} → {self.title} ({self.slug})"

    def clean(self):
        # Проверка уникальности позиции внутри доски
        if KanbanColumn.objects.filter(
            board=self.board,
            position=self.position
        ).exclude(pk=self.pk).exists():
            raise ValidationError(f"Позиция {self.position} уже занята на доске {self.board}")

        # Проверка уникальности slug внутри доски
        if KanbanColumn.objects.filter(
            board=self.board,
            slug=self.slug
        ).exclude(pk=self.pk).exists():
            raise ValidationError(f"Slug '{self.slug}' уже используется на доске {self.board}")


class StudentKanbanCard(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name="kanban_card"
    )
    column = models.ForeignKey(KanbanColumn, on_delete=models.CASCADE, related_name="cards")
    position = models.PositiveIntegerField("Позиция в колонке", default=0)

    class Meta:
        ordering = ['position']
        indexes = [
            models.Index(fields=['column']),
            models.Index(fields=['student']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['student'], name='one_card_per_student')
        ]

    def __str__(self):
        return f"{self.student.full_name} → {self.column}"

    def clean(self):
        # Проверка соответствия доски и категории студента
        board_slug = self.column.board.slug
        category = self.student.category

        if category in ['alabuga_start', 'alabuga_mulatki'] and board_slug != "alabuga-start":
            raise ValidationError("Студент категории Алабуга Старт не может быть на доске Политеха")

        if category in ['college', 'patriot'] and board_slug != "polytech":
            raise ValidationError("Студент категории Политех не может быть на доске Алабуга Старт")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)