# apps/kanban/services.py
from django.db import transaction
from django.db.models import F
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import StudentKanbanCard, KanbanColumn
from .exceptions import CardNotFound, ColumnNotFound, PositionConflict


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
    try:
        card = StudentKanbanCard.objects.select_for_update().get(student_id=card_id)
    except StudentKanbanCard.DoesNotExist:
        raise CardNotFound()

    try:
        target_column = KanbanColumn.objects.get(id=target_column_id, board=card.column.board)
    except KanbanColumn.DoesNotExist:
        raise ColumnNotFound()

    old_column_id = card.column_id

    # Перемещаем
    card.column = target_column
    card.position = new_position
    card.save()

    # Пересчёт позиций
    reorder_column_positions(old_column_id)
    reorder_column_positions(target_column_id)

    # Реал-тайм
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"kanban_{target_column.board.id}",
        {
            "type": "card.moved",
            "card_id": card_id,
            "from_column": old_column_id,
            "to_column": target_column_id,
            "position": new_position,
        }
    )

    return card