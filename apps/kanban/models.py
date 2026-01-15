from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

LEVEL_CHOICES = [
    ('black', 'Чёрный уровень'),
    ('red', 'Красный уровень'),
    ('yellow', 'Жёлтый уровень'),
    ('green', 'Зелёный уровень'),
]

class KanbanBoard(models.Model):
    id = models.CharField("ID доски", max_length=50, primary_key=True)  
    title = models.CharField("Название", max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="kanban_boards")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Канбан-доска"
        verbose_name_plural = "Канбан-доски"

    def __str__(self):
        return self.title

    def get_students(self):
        from apps.students.models import Student  # ← импорт внутри метода — нет цикла
        if self.id == "polytech":
            return Student.objects.exclude(category__in=['alabuga_mulatki'])
        elif self.id == "start":
            return Student.objects.filter(category__in=['alabuga_mulatki'])
        return Student.objects.none()


class KanbanColumn(models.Model):
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name="columns")
    level = models.CharField("Уровень", max_length=30, choices=LEVEL_CHOICES)
    title = models.CharField("Название колонки", max_length=100)
    color = models.CharField("Цвет (HEX)", max_length=7, default="#6B7280")
    position = models.PositiveSmallIntegerField("Позиция", default=0)

    class Meta:
        unique_together = ('board', 'level')
        ordering = ['position']
        indexes = [models.Index(fields=['board', 'level'])]

    def __str__(self):
        return f"{self.board.title} → {self.get_level_display()} ({self.level})"

    def clean(self):
        if KanbanColumn.objects.filter(
            board=self.board,
            position=self.position
        ).exclude(pk=self.pk).exists():
            raise ValidationError(f"Позиция {self.position} уже занята на доске {self.board}")


class StudentKanbanCard(models.Model):
    student = models.OneToOneField(
        'students.Student',  # ← строка вместо прямого импорта — ключевой фикс
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
        board_id = self.column.board.id
        # Импорт внутри метода — нет цикла
        from apps.students.models import Student
        category = self.student.category

        if category in ['alabuga_mulatki'] and board_id != 'start':
            raise ValidationError("Студент категории Алабуга Старт не может быть на доске Политеха")

        if category in ['alabuga_start', 'college', 'patriot'] and board_id != 'polytech':
            raise ValidationError("Студент категории Политех не может быть на доске Алабуга Старт")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)