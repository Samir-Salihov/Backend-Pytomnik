# apps/kanban/constants.py
from django.db import models


class ColumnType(models.TextChoices):
    BLACK = "black", "Чёрная зона"
    RED = "red", "Красная зона"
    YELLOW = "yellow", "Жёлтая зона"
    GREEN = "green", "Зелёная зона"
    HR_CALL = "hr_call", "Вызов к HR"
    FIRED = "fired", "Уволен"