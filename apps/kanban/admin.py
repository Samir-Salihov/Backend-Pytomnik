# apps/kanban/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import KanbanBoard, KanbanColumn, StudentKanbanCard


# Заголовок админки
admin.site.site_header = "Питомник — Администрирование"
admin.site.site_title = "Питомник"
admin.site.index_title = "Канбан и студенты"


# Инлайн карточек
class StudentKanbanCardInline(admin.TabularInline):
    model = StudentKanbanCard
    extra = 0
    fields = ('student_link', 'position')
    readonly_fields = ('student_link',)
    ordering = ('position',)

    def student_link(self, obj):
        if not obj.student:
            return "-"
        url = reverse("admin:students_student_change", args=[obj.student.id])
        return format_html(
            '<a href="{}" style="font-weight:600; color:#1d4ed8;">{} → {}</a>',
            url, obj.student.full_name, obj.student.get_level_display()
        )
    student_link.short_description = "Студент"


@admin.register(KanbanColumn)
class KanbanColumnAdmin(admin.ModelAdmin):
    list_display = ('id', 'colored_title', 'board', 'cards_count', 'position')
    list_editable = ('position',)
    inlines = [StudentKanbanCardInline]
    ordering = ('board', 'position')

    def colored_title(self, obj):
        return format_html(
            '<span style="padding:4px 8px; border-radius:6px; background:{}; color:white; font-weight:600;">{}</span>',
            obj.color or "#6B7280", obj.get_id_display()
        )
    colored_title.short_description = "Колонка"

    def cards_count(self, obj):
        count = obj.cards.count()
        return format_html('<b>{}</b>', count)
    cards_count.short_description = "Карточек"


@admin.register(StudentKanbanCard)
class StudentKanbanCardAdmin(admin.ModelAdmin):
    list_display = ('student_preview', 'column_colored', 'position', 'position', 'board_link')
    list_editable = ('position',)
    search_fields = ('student__first_name', 'student__last_name', 'student__patronymic')
    list_filter = ('column__board', 'column__id')
    ordering = ('column__board', 'column__position', 'position')

    def student_preview(self, obj):
        # БЕЗОПАСНО — если фото нет, будет заглушка
        photo_url = "/static/admin/img/placeholder.png"  # дефолтная картинка
        # Если вдруг появится поле photo — будет работать
        if hasattr(obj.student, 'photo') and obj.student.photo:
            photo_url = obj.student.photo.url

        return format_html(
            '''
            <div style="display:flex; align-items:center; gap:12px; min-width:200px;">
                <img src="{}" style="width:40px; height:40px; border-radius:50%; object-fit:cover; border:2px solid #e5e7eb;" />
                <div>
                    <div style="font-weight:600; color:#1e293b;">{}</div>
                    <small style="color:#64748b;">{} лет • {}</small>
                </div>
            </div>
            ''',
            photo_url,
            obj.student.full_name,
            obj.student.age,
            obj.student.get_level_display()
        )
    student_preview.short_description = "Студент"

    def column_colored(self, obj):
        return format_html(
            '<span style="padding:6px 12px; border-radius:8px; background:{}; color:white; font-weight:bold; font-size:13px;">{} → {}</span>',
            obj.column.color or "#6B7280",
            obj.column.board.title,
            obj.column.get_id_display()
        )
    column_colored.short_description = "Колонка"

    def board_link(self, obj):
        url = reverse("admin:kanban_kanbanboard_change", args=[obj.column.board.id])
        return format_html('<a href="{}" style="color:#3b82f6;">{} → {}</a>', url, obj.column.board.id, obj.column.board.title)
    board_link.short_description = "Доска"


@admin.register(KanbanBoard)
class KanbanBoardAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_by', 'created_at', 'total_cards', 'view_board')
    search_fields = ('id', 'title')
    readonly_fields = ('created_at',)

    def total_cards(self, obj):
        count = StudentKanbanCard.objects.filter(column__board=obj).count()
        return format_html('<b style="font-size:1.3em; color:#1d4ed8;">{}</b>', count)
    total_cards.short_description = "Всего карточек"

    def view_board(self, obj):
        url = f"/api/v1/kanban/{obj.id}/"  # или твой фронтенд
        return format_html(
            '<a href="{}" target="_blank" style="background:#10b981; color:white; padding:10px 20px; border-radius:8px; text-decoration:none; font-weight:bold;">Открыть канбан</a>',
            url
        )
    view_board.short_description = "Действия"