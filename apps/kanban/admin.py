from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import KanbanBoard, KanbanColumn, StudentKanbanCard


# Кастомный заголовок админки (можно оставить или убрать)
admin.site.site_header = "Питомник — Администрирование"
admin.site.site_title = "Питомник"
admin.site.index_title = "Канбан и колледжисты"


# Инлайн карточек колледжистов внутри колонки
class StudentKanbanCardInline(admin.TabularInline):
    model = StudentKanbanCard
    extra = 0
    fields = ('student_preview', 'position')
    readonly_fields = ('student_preview',)
    ordering = ('position',)

    def student_preview(self, obj):
        if not obj.student:
            return "—"
        url = reverse("admin:students_student_change", args=[obj.student.id])
        return format_html(
            '<a href="{}" style="font-weight:600; color:#1d4ed8;">{} → {}</a>',
            url, obj.student.full_name, obj.student.get_level_display()
        )
    student_preview.short_description = "Колледжист"


@admin.register(KanbanColumn)
class KanbanColumnAdmin(admin.ModelAdmin):
    list_display = (
        'colored_title',
        'board',
        'cards_count',
        'position',
    )
    list_editable = ('position',)
    list_filter = ('board',)
    search_fields = ('title', 'board__title')
    inlines = [StudentKanbanCardInline]
    ordering = ('board', 'position')

    def colored_title(self, obj):
        return format_html(
            '<span style="padding:6px 12px; border-radius:8px; background:{}; color:white; font-weight:600;">{}</span>',
            obj.color or "#6B7280", obj.get_level_display()
        )
    colored_title.short_description = "Колонка"

    def cards_count(self, obj):
        # Безопасный способ — считаем через фильтр по модели (не зависит от related_name)
        count = StudentKanbanCard.objects.filter(column=obj).count()
        return format_html('<b>{}</b>', count)
    cards_count.short_description = "Карточек"


@admin.register(StudentKanbanCard)
class StudentKanbanCardAdmin(admin.ModelAdmin):
    list_display = (
        'student_preview',
        'column_colored',
        'position',
        'board_link',
    )
    list_editable = ('position',)
    search_fields = (
        'student__first_name',
        'student__last_name',
        'student__patronymic',
    )
    list_filter = ('column__board', 'column__level')
    ordering = ('column__board', 'column__position', 'position')

    def student_preview(self, obj):
        photo_url = "/static/admin/img/icon-unknown.svg"
        if hasattr(obj.student, 'photo') and obj.student.photo:
            photo_url = obj.student.photo.url
        return format_html(
            '''
            <div style="display:flex; align-items:center; gap:12px; min-width:220px;">
                <img src="{}" style="width:44px; height:44px; border-radius:50%; object-fit:cover; border:2px solid #e5e7eb;" />
                <div>
                    <div style="font-weight:600; color:#1e293b;">{}</div>
                    <small style="color:#64748b;">{} лет • {}</small>
                </div>
            </div>
            ''',
            photo_url,
            obj.student.full_name,
            obj.student.age or "—",
            obj.student.get_level_display()
        )
    student_preview.short_description = "Колледжист"

    def column_colored(self, obj):
        return format_html(
            '<span style="padding:6px 12px; border-radius:8px; background:{}; color:white; font-weight:bold; font-size:13px;">{} → {}</span>',
            obj.column.color or "#6B7280",
            obj.column.board.title,
            obj.column.get_level_display()
        )
    column_colored.short_description = "Колонка"

    def board_link(self, obj):
        url = reverse("admin:kanban_kanbanboard_change", args=[obj.column.board.id])
        return format_html(
            '<a href="{}" style="color:#3b82f6; font-weight:600;">{}</a>',
            url, obj.column.board.title
        )
    board_link.short_description = "Доска"


@admin.register(KanbanBoard)
class KanbanBoardAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'created_by',
        'created_at',
        'total_cards',
        'view_board',
    )
    search_fields = ('id', 'title')
    list_filter = ('created_by',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    ordering = ('-created_at',)

    def total_cards(self, obj):
        count = StudentKanbanCard.objects.filter(column__board=obj).count()
        return format_html('<b style="font-size:1.3em; color:#1d4ed8;">{}</b>', count)
    total_cards.short_description = "Всего карточек"

    def view_board(self, obj):
        url = f"/api/v1/kanban/{obj.id}/"
        return format_html(
            '<a href="{}" target="_blank" style="background:#10b981; color:white; padding:8px 16px; border-radius:6px; text-decoration:none; font-weight:bold;">Открыть доску</a>',
            url
        )
    view_board.short_description = "Действия"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)