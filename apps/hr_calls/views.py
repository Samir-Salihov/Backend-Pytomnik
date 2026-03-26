from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authentication import SessionAuthentication
from django.shortcuts import get_object_or_404
from rest_framework import status

from utils.permissions import HRTEVOrAdminPermission
from .models import HrCall, HrComment, HrFile
from .services import generate_hr_calls_excel_stream
from .serializers import (
    HrCallSerializer, HrCallCreateSerializer, HrCallUpdateSerializer,
    HrCommentCreateSerializer, HrCommentSerializer, HrCommentUpdateSerializer,
    HrFileCreateSerializer, HrFileSerializer
)
from django.http import HttpResponse
from io import BytesIO
from django.utils import timezone


class HrCallListView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def get(self, request):
        calls = HrCall.objects.all().order_by('-created_at')
        serializer = HrCallSerializer(calls, many=True)
        return Response({
            "success": True,
            "calls": serializer.data
        }, status=status.HTTP_200_OK)


class HrCallDetailView(APIView):
    permission_classes = [HRTEVOrAdminPermission] 

    def get(self, request, pk):
        call = get_object_or_404(HrCall, pk=pk)
        serializer = HrCallSerializer(call)
        return Response({
            "success": True,
            "call": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk):
        """Полное обновление (PUT)"""
        call = get_object_or_404(HrCall, pk=pk)
        serializer = HrCallUpdateSerializer(call, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Вызов полностью обновлён",
                "call": HrCallSerializer(call).data
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Частичное обновление (PATCH) — можно менять только нужные поля"""
        call = get_object_or_404(HrCall, pk=pk)
        serializer = HrCallUpdateSerializer(call, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Вызов частично обновлён",
                "call": HrCallSerializer(call).data
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        call = get_object_or_404(HrCall, pk=pk)
        call.delete()
        return Response({
            "success": True,
            "message": "Вызов удалён"
        }, status=status.HTTP_204_NO_CONTENT)


class HrCallCreateView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def post(self, request):
        serializer = HrCallCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            call = serializer.save()
            return Response({
                "success": True,
                "message": "Вызов к HR создан",
                "call": HrCallSerializer(call).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class HrCommentListView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def get(self, request, pk):
        call = get_object_or_404(HrCall, pk=pk)
        comments = call.comments.all().order_by('-created_at')
        serializer = HrCommentSerializer(comments, many=True)
        return Response({
            "success": True,
            "comments": serializer.data
        }, status=status.HTTP_200_OK)


class HrCommentCreateView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def post(self, request, pk):
        call = get_object_or_404(HrCall, pk=pk)
        serializer = HrCommentCreateSerializer(data=request.data, context={'request': request, 'hr_call': call})
        if serializer.is_valid():
            comment = serializer.save()
            return Response({
                "success": True,
                "message": "Комментарий добавлен",
                "comment": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)





class HrCommentDetailView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def put(self, request, call_pk, pk):
        comment = get_object_or_404(HrComment, pk=pk, hr_call_id=call_pk)
        serializer = HrCommentUpdateSerializer(comment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Комментарий полностью обновлён",
                "comment": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, call_pk, pk):
        """Добавлен PATCH для комментариев (частичное обновление)"""
        comment = get_object_or_404(HrComment, pk=pk, hr_call_id=call_pk)
        serializer = HrCommentUpdateSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Комментарий частично обновлён",
                "comment": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, call_pk, pk):
        comment = get_object_or_404(HrComment, pk=pk, hr_call_id=call_pk)
        comment.delete()
        return Response({
            "success": True,
            "message": "Комментарий удалён"
        }, status=status.HTTP_204_NO_CONTENT)


class HrFileListView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def get(self, request, pk):
        call = get_object_or_404(HrCall, pk=pk)
        files = call.files.all().order_by('-uploaded_at')
        serializer = HrFileSerializer(files, many=True)
        return Response({
            "success": True,
            "files": serializer.data
        }, status=status.HTTP_200_OK)


class HrFileCreateView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def post(self, request, pk):
        call = get_object_or_404(HrCall, pk=pk)
        serializer = HrFileCreateSerializer(data=request.data, context={'request': request, 'hr_call': call})
        if serializer.is_valid():
            file = serializer.save()
            return Response({
                "success": True,
                "message": "Файл прикреплён",
                "file": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class HrFileDeleteView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def delete(self, request, call_pk, pk):
        file = get_object_or_404(HrFile, pk=pk, hr_call_id=call_pk)
        file.delete()
        return Response({
            "success": True,
            "message": "Файл удалён"
        }, status=status.HTTP_204_NO_CONTENT)


class HrCallExportExcelView(APIView):
    permission_classes = [HRTEVOrAdminPermission]

    def get(self, request):
        wb = generate_hr_calls_excel_stream()
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="hr_calls_{timezone.now():%Y%m%d_%H%M%S}.xlsx"'
        return response