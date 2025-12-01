# apps/users/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .serializers import CustomTokenObtainPairSerializer, RegisterSerializer


# ЛОГИН
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# РЕГИСТРАЦИЯ (только админ)
class RegisterView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Пользователь создан",
                "username": user.username,
                "role": user.role
            }, status=201)
        return Response(serializer.errors, status=400)


# Инфа о текущем юзере
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        return Response({
            "username": user.username,  
            "first_name": user.first_name,
            "last_name": user.last_name,
            "surname": user.surname,
            "role": user.role,
        })