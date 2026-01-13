# apps/students/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Student, LevelHistory, Comment, LEVEL_CHOICES  
from .serializers import (
    StudentSerializer,
    StudentCreateSerializer,
    StudentUpdateSerializer,
    LevelHistorySerializer,
    CommentListSerializer,
    CommentCreateSerializer,
    CommentUpdateSerializer
)


class StudentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        students = Student.objects.all().select_related('created_by', 'updated_by').order_by('-updated_at')
        serializer = StudentSerializer(students, many=True)
        return Response({
            "success": True,
            "count": students.count(),
            "students": serializer.data
        }, status=status.HTTP_200_OK)


class StudentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        serializer = StudentSerializer(student)
        return Response({
            "success": True,
            "student": serializer.data
        }, status=status.HTTP_200_OK)


class StudentCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = StudentCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            student = serializer.save()
            return Response({
                "success": True,
                "message": "Студент успешно создан",
                "student": {
                    "id": student.id,
                    "full_name": student.full_name,
                    "level": student.get_level_display(),
                    "status": student.get_status_display(),
                    "created_by": request.user.username
                }
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "message": "Ошибка при создании студента",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class StudentUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def put(self, request, pk):
        return self._update_student(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update_student(request, pk, partial=True)

    def _update_student(self, request, pk, partial=False):
        student = get_object_or_404(Student, pk=pk)
        serializer = StudentUpdateSerializer(
            student, 
            data=request.data, 
            context={'request': request},
            partial=partial  
        )
        if serializer.is_valid():
            updated_student = serializer.save()
            return Response({
                "success": True,
                "message": "Студент успешно обновлён",
                "student": {
                    "id": updated_student.id,
                    "full_name": updated_student.full_name,
                    "level": updated_student.get_level_display(),
                    "last_changed_field": updated_student.last_changed_field,
                    "updated_by": request.user.username
                }
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Ошибка при обновлении студента",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class StudentDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        full_name = student.full_name
        student.delete()
        return Response({
            "success": True,
            "message": f"Студент «{full_name}» успешно удалён"
        }, status=status.HTTP_200_OK)


class StudentChangeLevelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        new_level = request.data.get('new_level')
        comment = request.data.get('comment', '').strip()

        if new_level not in dict(LEVEL_CHOICES):
            return Response({
                "success": False,
                "message": "Недопустимый уровень"
            }, status=status.HTTP_400_BAD_REQUEST)

        old_level = student.level
        student.level = new_level
        student.updated_by = request.user
        student._change_comment = comment  
        student.save()  

        return Response({
            "success": True,
            "message": "Уровень успешно изменён",
            "student_id": student.id,
            "full_name": student.full_name,
            "old_level": old_level,
            "new_level": new_level,
            "changed_by": request.user.username,
            "comment": comment
        }, status=status.HTTP_200_OK)

class StudentLevelHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        history = student.level_history.all().order_by('-changed_at')
        serializer = LevelHistorySerializer(history, many=True)
        return Response({
            "success": True,
            "student_id": student.id,
            "full_name": student.full_name,
            "history": serializer.data
        }, status=status.HTTP_200_OK)


class StudentCommentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        comments = student.comments.all().order_by('-created_at')
        serializer = CommentListSerializer(comments, many=True)
        return Response({
            "success": True,
            "student_id": student.id,
            "comments": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        serializer = CommentCreateSerializer(
            data=request.data,
            context={'request': request, 'student': student}
        )
        if serializer.is_valid():
            comment = serializer.save()
            return Response({
                "success": True,
                "message": "Комментарий добавлен",
                "comment": CommentListSerializer(comment).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "message": "Ошибка при добавлении комментария",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CommentUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, student_pk, comment_pk):
        comment = get_object_or_404(Comment, pk=comment_pk, student_id=student_pk)

        if comment.author != request.user and not request.user.is_staff:
            return Response({
                "success": False,
                "message": "Вы не можете редактировать чужой комментарий"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = CommentUpdateSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            updated_comment = serializer.save()
            return Response({
                "success": True,
                "message": "Комментарий обновлён",
                "comment": CommentListSerializer(updated_comment).data
            }, status=status.HTTP_200_OK)

        return Response({
            "success": False,
            "message": "Ошибка при обновлении",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)