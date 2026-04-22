from rest_framework import serializers
from apps.students.models import Student
from .models import KanbanBoard, KanbanColumn, StudentKanbanCard
from utils.exceptions import (
    DuplicatePositionException, InvalidColorException,
    StudentCardAlreadyExistsException, IncompatibleCategoryBoardException
)


class StudentCardSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='student.id')
    full_name = serializers.CharField(source='student.full_name')
    photo = serializers.ImageField(source='student.photo', read_only=True)
    age = serializers.IntegerField(source='student.age')
    level = serializers.CharField(source='student.level')
    level_display = serializers.CharField(source='student.get_level_display')
    status = serializers.CharField(source='student.status')
    course = serializers.CharField(source='student.course')
    course_display = serializers.CharField(source='student.get_course_display')
    tags = serializers.SerializerMethodField()

    class Meta:
        model = StudentKanbanCard
        fields = ['id', 'full_name', 'photo', 'age', 'level', 'level_display', 'status', 'course', 'course_display', 'tags']

    def get_tags(self, obj: StudentKanbanCard):
        tags = []
        if obj.student.status == 'fired':
            tags.append({"text": "Уволен", "color": "#DC2626"})
        if obj.student.status == 'called_hr':
            tags.append({"text": "Вызов к HR", "color": "#F59E0B"})
        return tags


class KanbanColumnSerializer(serializers.ModelSerializer):
    cards = StudentCardSerializer(many=True, read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = KanbanColumn
        fields = ['id', 'level', 'level_display', 'title', 'color', 'cards']


class KanbanBoardSerializer(serializers.ModelSerializer):
    columns = KanbanColumnSerializer(many=True, read_only=True)
    column_order = serializers.SerializerMethodField()

    class Meta:
        model = KanbanBoard
        fields = ['id', 'title', 'columns', 'column_order']

    def get_column_order(self, obj):
        return [col.id for col in obj.columns.all().order_by('position')]


class KanbanColumnCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KanbanColumn
        fields = ['level', 'title', 'color', 'position']

    def validate_level(self, value):
        """Валидирует уровень"""
        from .models import LEVEL_CHOICES
        allowed_levels = [choice[0] for choice in LEVEL_CHOICES]
        if value not in allowed_levels:
            raise serializers.ValidationError(
                f"Неверный уровень. Допустимые значения: {', '.join(allowed_levels)}"
            )
        return value

    def validate_color(self, value):
        """Валидирует HEX цвет"""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise InvalidColorException(
                "Цвет должен быть в формате #RRGGBB (например, #FF5733)"
            )
        return value

    def validate_position(self, value):
        """Валидирует позицию"""
        if value < 0:
            raise serializers.ValidationError("Позиция не может быть отрицательной")
        return value

    def validate_title(self, value):
        """Валидирует название колонки"""
        if not value or not str(value).strip():
            raise serializers.ValidationError("Название колонки не может быть пустым")
        if len(str(value)) > 100:
            raise serializers.ValidationError("Название не может быть длиннее 100 символов")
        return value


class KanbanBoardCreateSerializer(serializers.ModelSerializer):
    columns = KanbanColumnCreateSerializer(many=True, required=False)

    class Meta:
        model = KanbanBoard
        fields = ['id', 'title', 'columns']

    def validate_id(self, value):
        """Валидирует ID доски"""
        if not value or not str(value).strip():
            raise serializers.ValidationError("ID доски не может быть пустым")
        if len(str(value)) > 50:
            raise serializers.ValidationError("ID не может быть длиннее 50 символов")
        if KanbanBoard.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Доска с ID '{value}' уже существует")
        return value

    def validate_title(self, value):
        """Валидирует название доски"""
        if not value or not str(value).strip():
            raise serializers.ValidationError("Название доски не может быть пустым")
        if len(str(value)) > 200:
            raise serializers.ValidationError("Название не может быть длиннее 200 символов")
        return value

    def create(self, validated_data):
        columns_data = validated_data.pop('columns', [])
        board = KanbanBoard.objects.create(**validated_data)

        # Создаём стандартные колонки + "Уволенные"
        if not columns_data:
            default_columns = [
                {'level': 'black', 'title': 'Чёрный уровень', 'color': '#000000', 'position': 1},
                {'level': 'red', 'title': 'Красный уровень', 'color': '#ef4444', 'position': 2},
                {'level': 'yellow', 'title': 'Жёлтый уровень', 'color': '#eab308', 'position': 3},
                {'level': 'green', 'title': 'Зелёный уровень', 'color': '#22c55e', 'position': 4},
                {'level': 'fired', 'title': 'Уволенные', 'color': '#6B7280', 'position': 5},
            ]
            columns_data = default_columns

        for column_data in columns_data:
            KanbanColumn.objects.create(board=board, **column_data)

        return board