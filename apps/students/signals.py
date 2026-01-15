from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import logging

from .models import Student, LevelHistory
from apps.kanban.models import KanbanBoard, KanbanColumn, StudentKanbanCard

logger = logging.getLogger(__name__)

# Определяем LEVEL_CHOICES здесь (чтобы не зависеть от модели)
LEVEL_CHOICES = [
    ('black', 'Чёрный уровень'),
    ('red', 'Красный уровень'),
    ('yellow', 'Жёлтый уровень'),
    ('green', 'Зелёный уровень'),
]


@receiver(pre_save, sender=Student)
def track_level_and_category_change(sender, instance, **kwargs):
    """
    Запоминаем старый уровень и категорию перед сохранением.
    """
    if instance.pk:
        try:
            old = sender.objects.only('level', 'category').get(pk=instance.pk)
            instance._previous_level = old.level
            instance._previous_category = old.category
        except sender.DoesNotExist:
            instance._previous_level = None
            instance._previous_category = None
    else:
        instance._previous_level = None
        instance._previous_category = None


@receiver(post_save, sender=Student)
def sync_kanban_card(sender, instance, created, **kwargs):
    """
    Автоматическая синхронизация карточки в канбане:
    - При создании кота — создаём карточку в доске по категории
    - При смене уровня — перемещаем карточку в нужную колонку (создаём колонку, если её нет)
    - При смене категории — удаляем старую карточку и создаём в новой доске
    """
    previous_level = getattr(instance, '_previous_level', None)
    previous_category = getattr(instance, '_previous_category', None)

    category_changed = previous_category is not None and previous_category != instance.category
    level_changed = previous_level is not None and previous_level != instance.level

    # 1. История уровней (только при обновлении и смене уровня)
    if not created and level_changed:
        comment = getattr(instance, '_change_comment', '')

        LevelHistory.objects.create(
            student=instance,
            old_level=previous_level,
            new_level=instance.level,
            changed_by=instance.updated_by,
            comment=comment
        )
        logger.info(f"Смена уровня кота {instance.full_name}: {previous_level} → {instance.level}")

    # 2. Определяем целевую доску по категории
    if instance.category == 'alabuga_mulatki':
        target_board_id = "start"  # ← твой ID доски для Алабуга Старт МИР
    else:
        target_board_id = "polytech"

    try:
        target_board = KanbanBoard.objects.get(id=target_board_id)
    except KanbanBoard.DoesNotExist:
        logger.warning(f"Доска {target_board_id} не найдена для кота {instance.id}")
        return

    # 3. Получаем или создаём колонку по уровню кота
    target_column, column_created = KanbanColumn.objects.get_or_create(
        board=target_board,
        level=instance.level,
        defaults={
            'title': dict(LEVEL_CHOICES).get(instance.level, instance.level),  # красивое название из choices
            'color': '#6B7280',  # дефолтный цвет
            'position': KanbanColumn.objects.filter(board=target_board).count() + 1  # в конец
        }
    )

    if column_created:
        logger.info(f"Автоматически создана колонка {instance.level} на доске {target_board_id}")

    # 4. Если категория изменилась — удаляем старую карточку
    if category_changed:
        StudentKanbanCard.objects.filter(student=instance).delete()
        logger.info(f"Удалена старая карточка кота {instance.full_name} при смене категории {previous_category} → {instance.category}")

    # 5. Создаём или обновляем карточку
    card, card_created = StudentKanbanCard.objects.update_or_create(
        student=instance,
        defaults={
            'column': target_column,
            'position': 9999  # в конец колонки
        }
    )

    if card_created:
        logger.info(f"Создана новая карточка для кота {instance.full_name} на доске {target_board_id}")
    elif card.column != target_column:
        logger.info(f"Перемещена карточка кота {instance.full_name} → {target_column.get_level_display()}")
    else:
        logger.debug(f"Карточка кота {instance.full_name} осталась на месте")

    # Очистка временных атрибутов
    for attr in ('_previous_level', '_previous_category', '_change_comment'):
        if hasattr(instance, attr):
            delattr(instance, attr)