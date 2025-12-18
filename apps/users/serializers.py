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
            "user": {
                "user_id": self.user.id,
                "username": self.user.username,
                "email": self.user.email or "",
                "telegram": self.user.telegram or "",
                "first_name": self.user.first_name or "",
                "last_name": self.user.last_name or "",
                "surname": self.user.surname or "",
                "role": self.user.role,
                "position": self.user.position or "",
                "avatar_url": self.user.avatar_url,
            }
        })
        return data


# === РЕГИСТРАЦИЯ ===
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Повторите пароль")

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "telegram",
            "first_name",
            "surname",
            "last_name",
            "role",
            "position",
            "bio",
            "password",
            "password2"
        )
        extra_kwargs = {
            'email': {'required': False},
            'telegram': {'required': False},
            'bio': {'required': False},
            'position': {'required': False},
        }

    def validate(self, attrs):
        # Проверка совпадения паролей
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        
        # Проверка, что указан хотя бы email или telegram
        if not attrs.get('email') and not attrs.get('telegram'):
            raise serializers.ValidationError({
                "email": "Укажите email или Telegram для связи",
                "telegram": "Укажите email или Telegram для связи"
            })
        
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        
        # Приводим telegram к нижнему регистру, если указан
        if 'telegram' in validated_data and validated_data['telegram']:
            validated_data['telegram'] = validated_data['telegram'].lower()
        
        user = User.objects.create_user(**validated_data)
        return user


# === СПИСОК ПОЛЬЗОВАТЕЛЕЙ ===
class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    telegram_link = serializers.SerializerMethodField()
    has_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'telegram',
            'telegram_link',
            'first_name',
            'last_name',
            'surname',
            'full_name',
            'role',
            'role_display',
            'position',
            'bio',
            'avatar_url',
            'has_avatar',
            'date_joined',
            'last_login',
            'is_active',
            'is_staff'
        )
        read_only_fields = ('date_joined', 'last_login', 'is_active', 'is_staff')
    
    def get_has_avatar(self, obj):
        """Проверяет, есть ли аватарка"""
        return bool(obj.avatar) 
    
    def get_full_name(self, obj):
        """Полное имя в формате 'Фамилия Имя Отчество'"""
        return obj.get_full_name()
    
    def get_role_display(self, obj):
        """Человеко-понятное отображение роли"""
        role_display_map = {
            'admin': 'Администратор',
            'hr': 'HR специалист',
            'saok': 'Сотрудник САОК',
            'med': 'Медицинский работник'
        }
        return role_display_map.get(obj.role, obj.role)
    
    def get_avatar_url(self, obj):
        """URL аватарки"""
        return obj.avatar_url
    
    def get_telegram_link(self, obj):
        """Ссылка на Telegram профиль"""
        return obj.telegram_link
    
    def get_has_avatar(self, obj):
        """Есть ли аватарка"""
        return obj.has_avatar



# apps/users/serializers.py (дополнительно)

# === ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ===
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "email",
            "telegram",
            "first_name",
            "last_name",
            "surname",
            "position",
            "bio",
            "avatar"
        )
        extra_kwargs = {
            'email': {'required': False},
            'telegram': {'required': False},
        }
    
    def validate_telegram(self, value):
        """Приводим telegram к нижнему регистру"""
        if value:
            return value.lower()
        return value
    
    def validate(self, attrs):
        # Проверка, что остался хотя бы один способ связи
        user = self.instance
        email = attrs.get('email', user.email)
        telegram = attrs.get('telegram', user.telegram)
        
        if not email and not telegram:
            raise serializers.ValidationError({
                "email": "Должен быть указан email или Telegram",
                "telegram": "Должен быть указан email или Telegram"
            })
        
        return attrs


# === СМЕНА ПАРОЛЯ ===
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        # Проверка совпадения новых паролей
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password": "Пароли не совпадают"})
        
        # Проверка, что новый пароль отличается от старого
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": "Новый пароль должен отличаться от старого"})
        
        return attrs