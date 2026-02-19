from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

LEVEL_CHOICES = [
    ('black', 'Чёрный уровень'),
    ('red', 'Красный уровень'),
    ('yellow', 'Жёлтый уровень'),
    ('green', 'Зелёный уровень'),
    ('fired', 'Уволен'),
    ('', 'Без уровня'),
]

COLOR_CHOICES = [
    ('#000000', 'Чёрный'),
    ('#ef4444', 'Красный'),
    ('#eab308', 'Жёлтый'),
    ('#22c55e', 'Зелёный'),
    ('#6B7280', 'Серый'),
    ("#662374", 'Фиолетовый'),
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
        from apps.students.models import Student
        if self.id == "polytech":
            return Student.objects.exclude(category__in=['alabuga_mulatki'])
        elif self.id == "start":
            return Student.objects.filter(category__in=['alabuga_mulatki'])
        return Student.objects.none()


class KanbanColumn(models.Model):
    board = models.ForeignKey('kanban.KanbanBoard', on_delete=models.CASCADE, related_name="columns")
    level = models.CharField("Уровень", max_length=30, choices=LEVEL_CHOICES)
    title = models.CharField("Название колонки", max_length=100)
    color = models.CharField("Цвет (HEX)", max_length=7, choices=COLOR_CHOICES)
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
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='kanban_card')
    column = models.ForeignKey('KanbanColumn', on_delete=models.CASCADE, related_name='cards')
    position = models.PositiveIntegerField(default=0)
    labels = models.JSONField(default=list, blank=True)

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
        category = self.student.category

        if category in ['alabuga_mulatki', 'alabuga_start_sng', 'patriot', 'alabuga_start_rf'] and board_id != 'start':
            raise ValidationError("Колледжист категории Алабуга Старт и Патриоты не может быть на доске Политеха")

        if category in ['college'] and board_id != 'polytech':
            raise ValidationError("Колледжист категории Политех не может быть на доске Алабуга Старт")

        # Убрана обязательность даты увольнения при перемещении в "Уволен"
        # Дата теперь опциональна

    def save(self, *args, **kwargs):
        self.clean()

        if self.column.level == 'fired':
            status = 'fired'
            level = 'fired'
        elif self.column.level == '':  # Без уровня
            status = 'active'
            level = ''
        else:
            status = 'active'
            level = self.column.level

        from apps.students.models import Student
        Student.objects.filter(id=self.student.id).update(status=status, level=level)

        super().save(*args, **kwargs)