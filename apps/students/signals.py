from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import logging

from .models import Student, LevelHistory
from apps.analytics.signals import update_analytics_snapshot

logger = logging.getLogger(__name__)

LEVEL_CHOICES_DICT = dict([
    ('black', 'Чёрный уровень'),
    ('red', 'Красный уровень'),
    ('yellow', 'Жёлтый уровень'),
    ('green', 'Зелёный уровень'),
    ('fired', 'Уволен'),
])


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
    Безопасная синхронизация карточки без рекурсии:
    - Создаём/обновляем карточку только если нужно
    - Используем .update() или .get_or_create() без save() на Student
    - Автоматически добавляем теги (labels) по категории
    """
    from apps.kanban.models import KanbanBoard, KanbanColumn, StudentKanbanCard

    previous_level = getattr(instance, '_previous_level', None)
    previous_category = getattr(instance, '_previous_category', None)

    category_changed = previous_category is not None and previous_category != instance.category
    level_changed = previous_level is not None and previous_level != instance.level

    # 1. История уровней (только при реальной смене уровня)
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
    if instance.category in ['patriot', 'alabuga_start_rf', 'alabuga_start_sng', 'alabuga_mulatki']:
        target_board_id = "start"
    else:
        target_board_id = "polytech"  # college и любые другие — на polytech

    try:
        target_board = KanbanBoard.objects.get(id=target_board_id)
    except KanbanBoard.DoesNotExist:
        logger.warning(f"Доска {target_board_id} не найдена для кота {instance.id}")
        return

    # 3. Получаем или создаём колонку по уровню кота
    target_column, column_created = KanbanColumn.objects.get_or_create(
        board=target_board,
        level=instance.level or 'fired',  # если level None — используем 'fired'
        defaults={
            'title': LEVEL_CHOICES_DICT.get(instance.level or 'fired', 'Уволен'),
            'color': '#6B7280' if instance.level == 'fired' else '#000000',
            'position': KanbanColumn.objects.filter(board=target_board).count() + 1
        }
    )

    if column_created:
        logger.info(f"Автоматически создана колонка {target_column.level} на доске {target_board_id}")

    # 4. Если категория изменилась — удаляем старую карточку
    if category_changed:
        StudentKanbanCard.objects.filter(student=instance).delete()
        logger.info(f"Удалена старая карточка кота {instance.full_name} при смене категории")

    # 5. Создаём или обновляем карточку — без вызова save на Student
    card, card_created = StudentKanbanCard.objects.update_or_create(
        student=instance,
        defaults={
            'column': target_column,
            'position': 9999  
        }
    )

    # 6. Автоматически добавляем теги (labels) по категории
    category_tags = {
        'patriot': ['Патриот'],
        'alabuga_start_rf': ['Алабуга РФ'],
        'alabuga_start_sng': ['Алабуга СНГ'],
        'alabuga_mulatki': ['Алабуга МИР'],
        'college': ['Колледжист'],
    }

    current_labels = card.labels or []  # если поле labels — JSONField(list)

    if instance.category in category_tags:
        for tag in category_tags[instance.category]:
            if tag not in current_labels:
                current_labels.append(tag)

    # Сохраняем обновлённые теги (только если изменились или создана карточка)
    if card_created or card.labels != current_labels:
        card.labels = current_labels
        card.save(update_fields=['labels'])

    # Очистка временных атрибутов
    for attr in ('_previous_level', '_previous_category', '_change_comment'):
        if hasattr(instance, attr):
            delattr(instance, attr)
    
    update_analytics_snapshot()