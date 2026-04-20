from rest_framework import serializers
from .models import HrCall, HrComment, HrFile
from django.utils import timezone
from utils.exceptions import (
    MissingStudentException, MissingFullNameException,
    InvalidPersonTypeException, AutomaticHrCallException,
    InvalidYearException, InvalidVisitDatetimeException
)
from utils.validators import validate_year, validate_datetime_not_future


class HrCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    is_edited_label = serializers.SerializerMethodField()

    class Meta:
        model = HrComment
        fields = ['id', 'author_username', 'text', 'created_at', 'updated_at', 'is_edited', 'is_edited_label']
        read_only_fields = fields

    def get_is_edited_label(self, obj):
        return "ред." if obj.is_edited else ""


class HrFileSerializer(serializers.ModelSerializer):
    file_url = serializers.FileField(source='file', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = HrFile
        fields = ['id', 'file_url', 'description', 'uploaded_at', 'uploaded_by_username']
        read_only_fields = fields


class HrCallSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    comments = HrCommentSerializer(many=True, read_only=True)
    files = HrFileSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    person_type_display = serializers.SerializerMethodField()

    class Meta:
        model = HrCall
        fields = [
            'id', 'person_type', 'person_type_display', 'category', 'student', 'full_name', 'reason', 'solution',
            'visit_datetime', 'created_by_username', 'created_at', 'updated_at',
            'comments', 'files', 'problem_resolved'
        ]
        read_only_fields = ['id', 'created_by_username', 'created_at', 'updated_at', 'comments', 'files']

    def get_full_name(self, obj):
        if obj.person_type == 'cat' and obj.student:
            return obj.student.full_name
        return obj.full_name
    
    def get_person_type_display(self, obj):
        return obj.get_person_type_display()


class HrCallCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrCall
        fields = ['person_type', 'student', 'full_name', 'reason', 'solution', 'visit_datetime']

    def validate_person_type(self, value):
        """Валидирует тип лица"""
        if value not in ['cat', 'not_cat']:
            raise InvalidPersonTypeException("Тип должен быть 'cat' (Кот) или 'not_cat' (Не кот)")
        return value

    def validate_full_name(self, value):
        """Валидирует ФИО"""
        if value and not str(value).strip():
            raise serializers.ValidationError("ФИО не может быть пустым")
        if value and len(str(value)) > 200:
            raise serializers.ValidationError("ФИО не может быть длиннее 200 символов")
        return value

    def validate_reason(self, value):
        """Валидирует причину вызова """
        if value and len(str(value)) > 2000:
            raise serializers.ValidationError("Причина не может быть длиннее 2000 символов")
        return value

    def validate_solution(self, value):
        """Валидирует решение"""
        if value and len(str(value)) > 2000:
            raise serializers.ValidationError("Решение не может быть длиннее 2000 символов")
        return value

    def validate_visit_datetime(self, value):
        """Валидирует дату и время посещения"""
        if value:
            try:
                validate_datetime_not_future(value)
            except Exception as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate(self, attrs):
        """Комплексная валидация"""
        person_type = attrs.get('person_type')
        student = attrs.get('student')
        full_name = attrs.get('full_name')
        
        # Для "кот" можно выбирать кота из базы (student). Если student не указан — требуем ФИО.
        if person_type == 'cat' and not student and not (full_name and str(full_name).strip()):
            raise MissingStudentException("Для типа 'cat' укажите кота (student) или заполните ФИО")

        # Для "не кот" — обязательное ФИО
        if person_type == 'not_cat' and not (full_name and str(full_name).strip()):
            raise MissingFullNameException("Для типа 'not_cat' необходимо указать ФИО")
        
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)


class HrCallUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления вызова к HR"""
    
    class Meta:
        model = HrCall
        fields = [
            'reason',           # Причина вызова
            'solution',         # Решение
            'visit_datetime',   # Дата и время посещения
            'problem_resolved'  # Проблема решена (галочка)
        ]
        extra_kwargs = {
            'reason': {'required': False, 'allow_blank': True},
            'solution': {'required': False, 'allow_blank': True},
            'visit_datetime': {'required': False, 'allow_null': True},
            'problem_resolved': {'required': False}
        }

    def validate_reason(self, value):
        """Валидирует причину вызова"""
        if value and len(str(value)) > 2000:
            raise serializers.ValidationError("Причина не может быть длиннее 2000 символов")
        return value

    def validate_solution(self, value):
        """Валидирует решение"""
        if value and len(str(value)) > 2000:
            raise serializers.ValidationError("Решение не может быть длиннее 2000 символов")
        return value

    def validate_visit_datetime(self, value):
        """Валидирует дату и время посещения"""
        if value:
            try:
                validate_datetime_not_future(value)
            except Exception as e:
                raise serializers.ValidationError(str(e))
        return value

    def update(self, instance, validated_data):
        # Обновляем поля, которые пришли в запросе
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Если проблема решена (problem_resolved = True) и это вызов для кота из базы
        if validated_data.get('problem_resolved') is True and instance.student:
            # Возвращаем статус студента на 'active'
            instance.student.status = 'active'
            instance.student.is_called_to_hr = False  # если есть такое поле
            instance.student.save(update_fields=['status', 'is_called_to_hr'])

        # Сохраняем изменения в вызове
        instance.save()

        return instance


class HrCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrComment
        fields = ['text']

    def create(self, validated_data):
        request = self.context.get('request')
        hr_call = self.context.get('hr_call')
        validated_data['author'] = request.user
        validated_data['hr_call'] = hr_call
        return super().create(validated_data)


class HrCommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrComment
        fields = ['text']

    def update(self, instance, validated_data):
        instance.text = validated_data['text']
        instance.save()
        return instance


class HrFileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrFile
        fields = ['file', 'description']

    def create(self, validated_data):
        request = self.context.get('request')
        hr_call = self.context.get('hr_call')
        validated_data['uploaded_by'] = request.user
        validated_data['hr_call'] = hr_call
        return super().create(validated_data)