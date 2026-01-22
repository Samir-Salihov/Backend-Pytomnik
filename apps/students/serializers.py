from rest_framework import serializers

from apps.kanban.models import StudentKanbanCard
from .models import Student, LevelHistory, Comment, MedicalFile
from django.contrib.auth import get_user_model

User = get_user_model()

class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    created_by_username = serializers.SerializerMethodField()
    updated_by_username = serializers.SerializerMethodField()

    level_history = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'patronymic', 'full_name',
            'direction', 'subdivision', 'age', 'level', 'level_display',
            'status', 'status_display', 'category', 'category_display',
            'address_actual', 'address_registered', 'phone_personal', 'telegram',
            'phone_parent', 'medical_info', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'updated_by', 'updated_by_username',
            'last_changed_field', 'level_history', 'comments', 'is_called_to_hr'
        ]
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'created_by', 'updated_by',
            'last_changed_field', 'level_history', 'comments'
        )

    def get_full_name(self, obj):
        return obj.full_name

    def get_created_by_username(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "—"

    def get_updated_by_username(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return "—"

    def get_level_history(self, obj):
        history = obj.level_history.all().order_by('-changed_at')[:20]
        return LevelHistorySerializer(history, many=True).data

    def get_comments(self, obj):
        comments = obj.comments.all().order_by('-created_at')
        return CommentListSerializer(comments, many=True).data


class StudentCreateSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True)  # ← можно загружать

    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'patronymic', 'direction', 'subdivision',
            'birth_date', 'photo', 'level', 'status', 'category',
            'address_actual', 'address_registered', 'phone_personal', 'telegram',
            'phone_parent', 'fio_parent', 'medical_info', 'is_called_to_hr'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'birth_date': {'required': True},
            'phone_personal': {'required': True},
            'level': {'required': True},
            'status': {'required': True},
            'category': {'required': True},
            'is_called_to_hr': {'required': False, 'default': False},
            'direction': {'required': True},
            'subdivision': {'required': True},
            'address_actual': {'required': True},
            'address_registered': {'required': True},
            'phone_parent': {'required': True},
            'fio_parent': {'required': True},
        }

    def validate(self, attrs):
        if attrs.get('phone_personal') == attrs.get('phone_parent'):
            raise serializers.ValidationError({
                "phone_parent": "Телефон родителя не может совпадать с личным телефоном."
            })
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        student = Student.objects.create(
            **validated_data,
            created_by=request.user,
            updated_by=request.user
        )
        return student


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'patronymic', 'direction', 'subdivision',
            'age', 'level', 'status', 'category', 'address_actual', 'address_registered',
            'phone_personal', 'telegram', 'phone_parent', 'medical_info', 'is_called_to_hr'
        ]

    def validate(self, attrs):
        if attrs.get('phone_personal') == attrs.get('phone_parent'):
            raise serializers.ValidationError({
                "phone_parent": "Телефон родителя не может совпадать с личным телефоном."
            })
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get('request')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = request.user
        instance.save()
        return instance


class LevelHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(
        source='changed_by.username',
        read_only=True,
        allow_null=True
    )
    changed_by_full_name = serializers.CharField(
        source='changed_by.get_full_name',
        read_only=True,
        default='—',
        allow_null=True
    )
    old_level_display = serializers.CharField(
        source='get_old_level_display',
        read_only=True
    )
    new_level_display = serializers.CharField(
        source='get_new_level_display',
        read_only=True
    )
    comment = serializers.CharField(
        read_only=True,
        allow_blank=True,
        default=''
    )

    class Meta:
        model = LevelHistory
        fields = [
            'id',
            'old_level',
            'old_level_display',
            'new_level',
            'new_level_display',
            'changed_by',
            'changed_by_username',
            'changed_by_full_name',  # ← добавлено: ФИО вместо username
            'changed_at',
            'comment'
        ]
        read_only_fields = (
            'id',
            'changed_by',
            'changed_by_username',
            'changed_by_full_name',
            'changed_at',
            'old_level',
            'new_level',
            'comment'
        )


class CommentListSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    is_edited_label = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'author_username', 'text', 'created_at', 'is_edited', 'is_edited_label']
        read_only_fields = fields

    def get_is_edited_label(self, obj):
        return "ред." if obj.is_edited else ""


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text']

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Комментарий не может быть пустым.")
        if len(value) > 2000:
            raise serializers.ValidationError("Максимум 2000 символов.")
        return value.strip()

    def create(self, validated_data):
        request = self.context.get('request')
        student = self.context.get('student')
        return Comment.objects.create(
            student=student,
            author=request.user,
            text=validated_data['text']
        )


class CommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text']

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Комментарий не может быть пустым.")
        if len(value) > 2000:
            raise serializers.ValidationError("Максимум 2000 символов.")
        return value.strip()

    def update(self, instance, validated_data):
        if instance.text != validated_data['text']:
            instance.is_edited = True
        instance.text = validated_data['text']
        instance.save()
        return instance


class StudentDetailSerializer(serializers.ModelSerializer):
    """
    Детальный сериализатор для одного студента — возвращает ВСЁ, что есть в модели.
    Используется в StudentDetailView для API /students/<pk>/
    """
    full_name = serializers.SerializerMethodField(read_only=True)
    age = serializers.SerializerMethodField(read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    photo_url = serializers.SerializerMethodField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    level_history = serializers.SerializerMethodField(read_only=True)
    comments = serializers.SerializerMethodField(read_only=True)
    medical_files = serializers.SerializerMethodField(read_only=True)
    kanban_card = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Student
        fields = [
            # Основные данные
            'id', 'first_name', 'last_name', 'patronymic', 'full_name',
            'direction', 'subdivision', 'birth_date', 'age',
            'level', 'level_display', 'status', 'status_display',
            'category', 'category_display', 'is_called_to_hr',
            
            # Контакты и адреса
            'address_actual', 'address_registered',
            'phone_personal', 'telegram', 'phone_parent', 'fio_parent',
            
            # Медицина и фото
            'medical_info', 'photo', 'photo_url', 'medical_files',
            
            # Системные поля
            'created_at', 'updated_at', 'created_by_username', 'updated_by_username',
            'last_changed_field',
            
            # Связи и история
            'level_history', 'comments', 'kanban_card',
        ]

    # Вычисляемые поля
    def get_full_name(self, obj):
        return obj.full_name

    def get_age(self, obj):
        return obj.age

    def get_photo_url(self, obj):
        if obj.photo:
            return obj.photo.url
        return "/static/images/default_student.png"  # ← укажи свой дефолтный путь

    def get_level_history(self, obj):
        history = obj.level_history.all().order_by('-changed_at')[:20]  # последние 20
        return LevelHistorySerializer(history, many=True).data

    def get_comments(self, obj):
        comments = obj.comments.all().order_by('-created_at')[:50]  # последние 50
        return CommentListSerializer(comments, many=True).data

    def get_medical_files(self, obj):
        files = obj.medical_files.all().order_by('-uploaded_at')
        return [
            {
                "id": f.id,
                "description": f.description,
                "file_url": f.file.url if f.file else None,
                "uploaded_at": f.uploaded_at.strftime("%d.%m.%Y %H:%M")
            }
            for f in files
        ]

    def get_kanban_card(self, obj):
        try:
            card = obj.kanban_card.first()  
            if not card:
                return None
            return {
                "id": card.id,
                "column_id": card.column.id,
                "column_title": card.column.title,
                "column_level": card.column.level,
                "position": card.position,
                "board_id": card.column.board.id,
                "board_title": card.column.board.title,
                "labels": card.labels  
            }
        except Exception:
            return None

class MedicalFileSerializer(serializers.ModelSerializer):
    file_url = serializers.FileField(source='file', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = MedicalFile
        fields = ['id', 'file_url', 'description', 'uploaded_at', 'uploaded_by_username']
        read_only_fields = fields

class MedicalFileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalFile
        fields = ['file', 'description']

    def create(self, validated_data):
        request = self.context.get('request')
        student = self.context.get('student')
        validated_data['uploaded_by'] = request.user
        validated_data['student'] = student
        return super().create(validated_data)