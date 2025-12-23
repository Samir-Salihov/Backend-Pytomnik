# apps/kanban/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from .models import KanbanBoard, StudentKanbanCard, KanbanColumn
from .serializers import KanbanBoardSerializer
from apps.students.models import Student, LevelHistory

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
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        card_id = request.data.get("cardId")
        column_id = request.data.get("columnId")
        position = request.data.get("position", 0)

        if not card_id or not column_id:
            return Response({"success": False, "message": "cardId и columnId обязательны"}, status=status.HTTP_400_BAD_REQUEST)

        card = get_object_or_404(StudentKanbanCard, id=card_id)
        new_column = get_object_or_404(KanbanColumn, id=column_id)

        card.student.level = new_column.id
        card.student.updated_by = request.user
        card.student.save() 

        card.column = new_column
        card.position = position
        card.save()

        return Response({"success": True, "message": "Карточка перемещена"})