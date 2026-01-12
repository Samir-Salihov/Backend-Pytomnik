# apps/students/serializers.py — добавь в конец
from rest_framework import serializers
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from .documents import StudentDocument

class StudentDocumentSerializer(DocumentSerializer):
    class Meta:
        document = StudentDocument
        fields = (
            'id', 'full_name', 'age', 'level', 'status', 'category',
            'phone_personal', 'telegram', 'subdivision'
        )