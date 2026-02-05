from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from .models import KanbanBoard, StudentKanbanCard, KanbanColumn
from .serializers import KanbanBoardSerializer, KanbanBoardCreateSerializer
from apps.students.models import Student, LevelHistory
from utils.permissions import (
    HRTEVOrAdminPermission,
    HRCorpOrTEVPermission,
    HRACOrTEVPermission,
    ROLE_HR_TEV,
)


class KanbanBoardDetailView(APIView):
    """
    HR-ТЕВ: полный доступ (чтение + просмотр карточек)
    HR-Корп.Развитие: чтение только для AS/Patriots + College (без просмотра карточки, без изменения уровня)
    HR-AC: чтение только для AS/Patriots (без просмотра карточки, без изменения уровня)
    """
    permission_classes = [HRTEVOrAdminPermission]

    def get(self, request, board_id):
        board = get_object_or_404(
            KanbanBoard.objects.prefetch_related('columns__cards__student'),
            id=board_id  
        )
        serializer = KanbanBoardSerializer(board)
        return Response(serializer.data)


class MoveCardView(APIView):
    """
    Только HR-ТЕВ может перемещать карточки (менять уровень).
    HR-Корп.Развитие и HR-AC не могут менять уровень.
    """
    permission_classes = [HRTEVOrAdminPermission]

    @transaction.atomic
    def post(self, request):
        # Проверяем, что только HR-ТЕВ или Админ могут менять уровень
        user = request.user
        if not user.is_superuser and getattr(user, "role", None) != ROLE_HR_TEV:
            return Response(
                {"success": False, "message": "Только HR-ТЕВ могут менять уровень"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        card_id = request.data.get("cardId")
        column_id = request.data.get("columnId")
        position = request.data.get("position", 0)

        if not card_id or not column_id:
            return Response({"success": False, "message": "cardId и columnId обязательны"}, status=status.HTTP_400_BAD_REQUEST)

        card = get_object_or_404(StudentKanbanCard, id=card_id)
        new_column = get_object_or_404(KanbanColumn, id=column_id)

        old_level = card.student.level

        card.column = new_column
        card.position = position
        card.save()  

        return Response({"success": True, "message": "Карточка перемещена"})


class KanbanBoardCreateView(APIView):
    """Только Админ может создавать доски."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = KanbanBoardCreateSerializer(data=request.data)
        if serializer.is_valid():
            board = serializer.save(created_by=request.user)
            return Response({
                "success": True,
                "message": "Канбан-доска успешно создана",
                "board": {
                    "id": board.id,
                    "title": board.title,
                    "columns_count": board.columns.count()
                }
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)