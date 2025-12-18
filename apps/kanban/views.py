# apps/kanban/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import KanbanBoard
from .serializers import KanbanBoardSerializer
from .services import move_student_card
from .permissions import IsHRorAdmin, CanMoveCard
from .exceptions import KanbanAPIException


class KanbanBoardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, board_id: str):
        board = get_object_or_404(
            KanbanBoard.objects.prefetch_related('columns__cards__student'),
            id=board_id
        )
        serializer = KanbanBoardSerializer(board)
        return Response(serializer.data)


class MoveCardView(APIView):
    permission_classes = [IsAuthenticated, CanMoveCard]

    def post(self, request):
        card_id = request.data.get("cardId")  # ID студента
        column_id = request.data.get("columnId")
        position = request.data.get("position", 0)

        if not card_id or not column_id:
            raise KanbanAPIException(detail="cardId и columnId обязательны")

        try:
            move_student_card(card_id=int(card_id), target_column_id=column_id, new_position=position)
        except Exception as e:
            raise KanbanAPIException(detail=str(e))

        return Response({"success": True, "message": "Карточка перемещена"})