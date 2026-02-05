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
    ROLE_HR_CORP,
    ROLE_HR_AC,
    ROLE_ADMIN,
    ROLE_MED,
)


class KanbanBoardDetailView(APIView):
    """
    HR-ТЕВ: полный доступ (чтение + просмотр карточек)
    HR-Корп.Развитие: просмотр карточек для досок polytech + start (без detail карточки, без изменения уровня)
    HR-AC: просмотр карточек только для доски start (без detail карточки, без изменения уровня)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, board_id):
        board = get_object_or_404(
            KanbanBoard.objects.prefetch_related('columns__cards__student'),
            id=board_id
        )

        user = request.user

        # full access for superuser, admin role and HR-TEV
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', None) in (ROLE_HR_TEV, ROLE_ADMIN):
            serializer = KanbanBoardSerializer(board)
            return Response(serializer.data)

        # HR-Corp: can view boards 'polytech' and 'start' with cards visible (but cannot open card details)
        if getattr(user, 'role', None) == ROLE_HR_CORP:
            if board.id in ('polytech', 'start'):
                serializer = KanbanBoardSerializer(board)
                return Response(serializer.data)
            return Response({'detail': 'Доступ запрещён', 'message': 'Вы не имеете прав на просмотр этой доски'}, status=status.HTTP_403_FORBIDDEN)

        # HR-AC: can view only board 'start' with cards visible (but cannot open card details)
        if getattr(user, 'role', None) == ROLE_HR_AC:
            if board.id == 'start':
                serializer = KanbanBoardSerializer(board)
                return Response(serializer.data)
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)

        return Response({'detail': 'Доступ запрещён', 'message': 'Вы не имеете прав на просмотр этой доски'}, status=status.HTTP_403_FORBIDDEN)


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