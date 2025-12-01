# apps/users/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
from django.contrib.auth.password_validation import validate_password


# === ЛОГИН ===
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data.update({
            "user_id": self.user.id,
            "username": self.user.username,
            "first_name": self.user.first_name or "",
            "last_name": self.user.last_name or "",
            "surname": self.user.surname or "",
            "role": self.user.role,
        })
        return data


# === РЕГИСТРАЦИЯ ===
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Повторите пароль")


    class Meta:
        model = User
        fields = ("username", "first_name", "surname", "last_name", "role", "password", "password2")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(**validated_data)
        return user