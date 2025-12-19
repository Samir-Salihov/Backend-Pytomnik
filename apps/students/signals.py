# apps/students/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Student, LevelHistory
from apps.kanban.models import KanbanBoard, KanbanColumn, StudentKanbanCard

@receiver(pre_save, sender=Student)
def track_level_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Student.objects.get(pk=instance.pk)
            instance._old_level = old_instance.level
        except Student.DoesNotExist:
            instance._old_level = None
    else:
        instance._old_level = None

@receiver(post_save, sender=Student)
def sync_kanban_and_history(sender, instance, created, **kwargs):
    # История уровней
    if not created:
        old_level = getattr(instance, '_old_level', None)
        if old_level is not None and old_level != instance.level:
            LevelHistory.objects.create(
                student=instance,
                old_level=old_level,
                new_level=instance.level,
                changed_by=instance.updated_by,
                comment=""
            )

    # Синхронизация с канбаном
    try:
        board = KanbanBoard.objects.get(id="polytech")
        target_column = KanbanColumn.objects.get(id=instance.level, board=board)
    except (KanbanBoard.DoesNotExist, KanbanColumn.DoesNotExist):
        return

    card, card_created = StudentKanbanCard.objects.get_or_create(
        student=instance,
        defaults={'column': target_column, 'position': 9999}
    )

    if not card_created and card.column.id != instance.level:
        card.column = target_column
        card.position = 9999
        card.save()

    if hasattr(instance, '_old_level'):
        del instance._old_level