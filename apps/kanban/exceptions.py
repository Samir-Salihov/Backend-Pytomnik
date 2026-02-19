# apps/kanban/exceptions.py
from rest_framework.exceptions import APIException
from rest_framework import status


class KanbanAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Ошибка в канбан-доске"
    default_code = "kanban_error"


class BoardNotFound(KanbanAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Канбан-доска не найдена"
    default_code = "board_not_found"


class ColumnNotFound(KanbanAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Колонка не найдена"
    default_code = "column_not_found"


class CardNotFound(KanbanAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Карточка колледжиста не найдена"
    default_code = "card_not_found"


class InvalidColumnTransition(KanbanAPIException):
    default_detail = "Недопустимый переход между колонками"
    default_code = "invalid_transition" 


class PositionConflict(KanbanAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Конфликт позиций при перемещении"
    default_code = "position_conflict"


class PermissionDenied(KanbanAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Нет прав на выполнение действия"
    default_code = "permission_denied"