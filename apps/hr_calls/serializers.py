from rest_framework import serializers
from .models import HrCall, HrComment, HrFile


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
    problem_resolved = serializers.BooleanField(read_only=True)  # readonly для фронта

    class Meta:
        model = HrCall
        fields = [
            'id', 'person_type', 'student', 'full_name', 'reason', 'solution',
            'visit_datetime', 'problem_resolved', 'created_by_username', 'created_at', 'updated_at',
            'comments', 'files'
        ]
        read_only_fields = ['id', 'created_by_username', 'created_at', 'updated_at', 'comments', 'files', 'problem_resolved']

    def get_full_name(self, obj):
        if obj.person_type == 'student' and obj.student:
            return obj.student.full_name
        return obj.full_name


class HrCallCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrCall
        fields = ['person_type', 'student', 'full_name', 'reason', 'solution', 'visit_datetime']

    def validate(self, attrs):
        if attrs['person_type'] == 'student':
            raise serializers.ValidationError({"person_type": "Для котов вызов создаётся автоматически при смене статуса"})
        if attrs['person_type'] == 'college' and not attrs.get('full_name'):
            raise serializers.ValidationError({"full_name": "Для колледжиста укажите ФИО"})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)


class HrCallUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrCall
        fields = ['reason', 'solution', 'visit_datetime']

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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