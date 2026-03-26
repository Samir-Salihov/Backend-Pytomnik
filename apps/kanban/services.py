# apps/kanban/services.py
from django.db import transaction
from django.db.models import F
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError
from .models import StudentKanbanCard, KanbanColumn
from .exceptions import CardNotFound, ColumnNotFound, PositionConflict, InvalidColumnTransition, KanbanAPIException


def reorder_column_positions(column_id: str) -> None:
    """Атомарно пересчитывает позиции в колонке"""
    from django.db.models import Case, When, IntegerField

    cards = StudentKanbanCard.objects.filter(column_id=column_id).order_by('position', 'id')
    preserved_order = [card.id for card in cards]
    
    if preserved_order:
        when_clauses = [When(pk=pk, then=pos) for pos, pk in enumerate(preserved_order)]
        StudentKanbanCard.objects.filter(pk__in=preserved_order).update(
            position=Case(*when_clauses, output_field=IntegerField())
        )


@transaction.atomic
def move_student_card(card_id: int, target_column_id: str, new_position: int):
    """Перемещает карточку с полной защитой от гонок"""
    # Валидация входных данных
    if not isinstance(card_id, int) or card_id <= 0:
        raise ValueError("Invalid card_id: must be a positive integer")
    
    if not isinstance(target_column_id, str) or not target_column_id.strip():
        raise ValueError("Invalid target_column_id: must be a non-empty string")
    
    if not isinstance(new_position, int) or new_position < 0:
        raise ValueError("Invalid new_position: must be a non-negative integer")

    try:
        # Используем select_for_update для защиты от гонок
        card = StudentKanbanCard.objects.select_for_update().get(student_id=card_id)
    except StudentKanbanCard.DoesNotExist:
        raise CardNotFound()

    try:
        # Проверяем, что целевая колонка принадлежит той же доске
        target_column = KanbanColumn.objects.select_for_update().get(
            id=target_column_id, 
            board=card.column.board
        )
    except KanbanColumn.DoesNotExist:
        raise ColumnNotFound()

    old_column_id = card.column_id

    # Проверка валидности перехода между колонками
    try:
        # Создаем временный объект для проверки валидации
        temp_card = StudentKanbanCard(
            student=card.student,
            column=target_column,
            position=new_position
        )
        temp_card.clean()
    except ValidationError as e:
        raise InvalidColumnTransition(detail=str(e))

    # Сохраняем изменения
    card.column = target_column
    card.position = new_position
    
    try:
        card.save()
    except Exception as e:
        # Ловим любые ошибки сохранения
        raise KanbanAPIException(detail=f"Failed to save card: {str(e)}")

    # Пересчёт позиций в обеих колонках
    try:
        reorder_column_positions(old_column_id)
        reorder_column_positions(target_column_id)
    except Exception as e:
        # Если пересчет позиций не удался, откатываем транзакцию
        raise KanbanAPIException(detail=f"Failed to reorder positions: {str(e)}")

    # Отправка реал-тайм уведомления
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"kanban_{target_column.board.id}",
            {
                "type": "card.moved",
                "card_id": card_id,
                "from_column": old_column_id,
                "to_column": target_column_id,
                "position": new_position,
                "student_id": card.student.id,
                "student_name": card.student.full_name,
            }
        )
    except Exception as e:
        # Ошибка отправки уведомления не должна откатывать транзакцию
        # Логируем ошибку, но не прерываем выполнение
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to send real-time notification: {str(e)}")

    return card
