# apps/kanban/serializers.py
from rest_framework import serializers
from apps.students.models import Student
from .models import KanbanBoard, KanbanColumn, StudentKanbanCard

class StudentCardSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='student.id')
    full_name = serializers.CharField(source='student.full_name')
    photo = serializers.ImageField(source='student.photo', read_only=True)
    age = serializers.IntegerField(source='student.age')
    level = serializers.CharField(source='student.level')
    level_display = serializers.CharField(source='student.get_level_display')
    status = serializers.CharField(source='student.status')
    tags = serializers.SerializerMethodField()

    class Meta:
        model = StudentKanbanCard
        fields = ['id', 'full_name', 'photo', 'age', 'level', 'level_display', 'status', 'tags']

    def get_tags(self, obj: StudentKanbanCard):
        tags = []
        if obj.student.status == 'fired':
            tags.append({"text": "Уволен", "color": "#DC2626"})
        if obj.student.status == 'called_hr':
            tags.append({"text": "Вызов к HR", "color": "#F59E0B"})
        return tags

class KanbanColumnSerializer(serializers.ModelSerializer):
    cards = StudentCardSerializer(many=True, read_only=True)

    class Meta:
        model = KanbanColumn
        fields = ['id', 'title', 'color', 'cards']

class KanbanBoardSerializer(serializers.ModelSerializer):
    columns = KanbanColumnSerializer(many=True, read_only=True)
    column_order = serializers.SerializerMethodField()

    class Meta:
        model = KanbanBoard
        fields = ['id', 'title', 'columns', 'column_order']

    def get_column_order(self, obj):
        return [col.id for col in obj.columns.all().order_by('position')]