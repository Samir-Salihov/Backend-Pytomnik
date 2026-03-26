from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db.models import Count
from django.utils import timezone
from apps.students.models import Student, LevelHistory
from apps.hr_calls.models import HrCall


# Сигналы для аналитики больше не нужны, так как аналитика теперь генерируется динамически
# без использования снимков в базе данных