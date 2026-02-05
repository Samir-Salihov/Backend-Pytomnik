# apps/users/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework import status
from .serializers import (
    CustomTokenObtainPairSerializer, 
    RegisterSerializer, 
    UserListSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer
)
from django.db.models import Case, When, Value, IntegerField
from .models import User
from utils.permissions import AdminOrSuperuserPermission, HRTEVOrAdminPermission


# ЛОГИН
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# РЕГИСТРАЦИЯ (только админ)
class RegisterView(APIView):
    permission_classes = [AdminOrSuperuserPermission]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Пользователь создан",
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": user.get_full_name()
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Инфа о текущем юзере
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserListSerializer(user)
        return Response(serializer.data)
    
    def put(self, request):
        """Обновление профиля текущего пользователя"""
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Профиль обновлен",
                "user": UserListSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Частичное обновление профиля"""
        return self.put(request)


# Смена пароля текущего пользователя
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            
            # Проверяем старый пароль
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": "Неверный пароль"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Устанавливаем новый пароль
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({
                "message": "Пароль успешно изменен"
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# СПИСОК ПОЛЬЗОВАТЕЛЕЙ
class UserListView(APIView):
    permission_classes = [HRTEVOrAdminPermission]
    
    def get(self, request):
        # Проверяем права доступа (админ и HR-ТЕВ могут видеть всех пользователей)
        
        # Определяем порядок сортировки ролей
        role_order = {
            'admin': 1,
            'hr_tev': 2,
            'hr_corp': 3,
            'hr_ac': 4,
            'med': 5
        }
        
        # Аннотируем пользователей числовым значением для сортировки
        users = User.objects.annotate(
            role_order=Case(
                When(role='admin', then=Value(1)),
                When(role='hr_tev', then=Value(2)),
                When(role='hr_corp', then=Value(3)),
                When(role='hr_ac', then=Value(4)),
                When(role='med', then=Value(5)),
                default=Value(6),
                output_field=IntegerField()
            )
        ).order_by('role_order', 'last_name', 'first_name')
        
        serializer = UserListSerializer(users, many=True)
        
        # Форматируем ответ с группировкой по ролям
        grouped_users = {
            'admin': [],
            'hr_tev': [],
            'hr_corp': [],
            'hr_ac': [],
            'med': []
        }
        
        for user_data in serializer.data:
            role = user_data['role']
            if role in grouped_users:
                grouped_users[role].append(user_data)
        
        return Response({
            'count': users.count(),
            'users_by_role': grouped_users,
            'users_list': serializer.data  
        })


# Детальная информация о пользователе и управление (только для админа)
class UserDetailView(APIView):
    permission_classes = [AdminOrSuperuserPermission]
    parser_classes = [MultiPartParser, JSONParser]
    
    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            serializer = UserListSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, pk):
        """Обновление пользователя админом"""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Пользователь обновлен",
                "user": UserListSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Частичное обновление пользователя"""
        return self.put(request, pk)
    
    def delete(self, request, pk):
        """Деактивация пользователя (мягкое удаление)"""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Не позволяем удалить себя самого
        if user == request.user:
            return Response(
                {"error": "Вы не можете деактивировать свой собственный аккаунт"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = False
        user.save()
        
        return Response({
            "message": f"Пользователь {user.username} деактивирован",
            "user_id": user.id,
            "username": user.username,
            "is_active": user.is_active
        })


# Активация пользователя (только админ)
class ActivateUserView(APIView):
    permission_classes = [AdminOrSuperuserPermission]
    
    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.is_active = True
        user.save()
        
        return Response({
            "message": f"Пользователь {user.username} активирован",
            "user_id": user.id,
            "username": user.username,
            "is_active": user.is_active
        })


# Получение пользователей по роли
class UsersByRoleView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, role):
        # Проверяем, что роль существует
        valid_roles = ['admin', 'hr_tev', 'hr_corp', 'hr_ac', 'med']
        if role not in valid_roles:
            return Response(
                {"error": f"Неверная роль. Допустимые значения: {', '.join(valid_roles)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем права доступа
        user_role = request.user.role
        if user_role not in ['admin'] and user_role != role:
            if not request.user.is_superuser:
                return Response(
                    {"error": "Вы можете видеть только пользователей своей роли или быть администратором"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        users = User.objects.filter(role=role, is_active=True).order_by('last_name', 'first_name')
        serializer = UserListSerializer(users, many=True)
        
        return Response({
            'role': role,
            'role_display': dict(User._meta.get_field('role').choices).get(role, role),
            'count': users.count(),
            'users': serializer.data
        })