# apps/students/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Student, LevelHistory

User = get_user_model()

@receiver(pre_save, sender=Student)
def create_level_history(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old = Student.objects.get(pk=instance.pk)
        if old.level != instance.level:
            LevelHistory.objects.create(
                student=instance,
                old_level=old.level,
                new_level=instance.level,
                changed_by=getattr(instance, 'updated_by', None),
                comment="Смена уровня доступа"
            )
    except Student.DoesNotExist:
        pass