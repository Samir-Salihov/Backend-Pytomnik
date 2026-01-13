from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import logging

from .models import Student, LevelHistory
from apps.kanban.models import KanbanBoard, KanbanColumn, StudentKanbanCard

logger = logging.getLogger(__name__)


from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Student, LevelHistory
from apps.kanban.models import KanbanBoard, KanbanColumn, StudentKanbanCard


@receiver(pre_save, sender=Student)
def track_level_change(sender, instance, **kwargs):
    """
    Запоминаем старый уровень перед сохранением.
    """
    if instance.pk:
        try:
            old = sender.objects.only('level').get(pk=instance.pk)
            instance._previous_level = old.level
        except sender.DoesNotExist:
            instance._previous_level = None
    else:
        instance._previous_level = None


@receiver(post_save, sender=Student)
def sync_kanban_and_history(sender, instance, created, **kwargs):
    """
    1. Создаём запись в истории уровней ТОЛЬКО здесь (если уровень изменился)
    2. Синхронизируем карточку в канбане
    """
    # 1. История уровней — ТОЛЬКО ОДНА запись на смену
    previous_level = getattr(instance, '_previous_level', None)
    if previous_level is not None and previous_level != instance.level:
        comment = getattr(instance, '_change_comment', '')  # комментарий из view, если передан

        LevelHistory.objects.create(
            student=instance,
            old_level=previous_level,
            new_level=instance.level,
            changed_by=instance.updated_by,
            comment=comment
        )

    # 2. Канбан-синхронизация (оставляем как есть)
    if instance.category in ['alabuga_start', 'alabuga_mulatki']:
        board_slug = "alabuga-start"
    else:
        board_slug = "polytech"

    try:
        board = KanbanBoard.objects.get(slug=board_slug)
        target_column = KanbanColumn.objects.get(board=board, slug=instance.level)
    except (KanbanBoard.DoesNotExist, KanbanColumn.DoesNotExist):
        return

    StudentKanbanCard.objects.update_or_create(
        student=instance,
        defaults={
            'column': target_column,
            'position': 9999
        }
    )

    # Очистка временных полей
    for attr in ('_previous_level', '_change_comment'):
        if hasattr(instance, attr):
            delattr(instance, attr)