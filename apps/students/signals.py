from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from apps.hr_calls.models import HrCall

from .models import Student, LevelHistory, LevelByMonth
from apps.analytics.signals import update_analytics_snapshot

logger = logging.getLogger(__name__)

LEVEL_CHOICES_DICT = dict([
    ('black', 'Чёрный уровень'),
    ('red', 'Красный уровень'),
    ('yellow', 'Жёлтый уровень'),
    ('green', 'Зелёный уровень'),
    ('fired', 'Уволен'),
    ('', 'Без уровня'),
])

YEARS = range(2023, 2027)

def get_current_year_month():
    now = timezone.now()
    return now.year, now.month

def initialize_level_calendar(student):
    """Инициализирует весь календарь (2023-2026) с "Без уровня" для новых студентов"""
    current_year, current_month = get_current_year_month()
    for year in YEARS:
        for month in range(1, 13):
            # Не создаём для будущих месяцев текущего года или будущих лет
            if year > current_year or (year == current_year and month > current_month):
                continue
            
            LevelByMonth.objects.get_or_create(
                student=student,
                year=year,
                month=month,
                defaults={
                    'level': '',  # Без уровня по умолчанию
                    'fired_date': None,
                    'last_changed_at': timezone.now(),
                    'change_count': 0
                }
            )

def update_level_by_month(student, level, fired_date=None, changed_by=None, comment='', create_history=True):
    year, month = get_current_year_month()

    # Создаём запись в LevelHistory (только если флаг разрешает)
    old_level = student.level
    if old_level != level and create_history:
        LevelHistory.objects.create(
            student=student,
            old_level=old_level,
            new_level=level,
            changed_by=changed_by,
            comment=comment
        )

    # Обновляем LevelByMonth для текущего месяца
    lbm, created = LevelByMonth.objects.get_or_create(
        student=student,
        year=year,
        month=month,
        defaults={
            'level': level,
            'fired_date': fired_date if level == 'fired' else None,
            'last_changed_at': timezone.now(),
            'change_count': 1
        }
    )
    if not created:
        lbm.level = level
        lbm.fired_date = fired_date if level == 'fired' else None
        lbm.last_changed_at = timezone.now()
        lbm.change_count += 1
        lbm.save()

    # Если уровень 'fired' — наследуем на все последующие месяцы
    if level == 'fired':
        propagate_fired(student, year, month, fired_date)

    # Если снимаем 'fired' — очищаем последующие месяцы от fired
    if old_level == 'fired' and level != 'fired':
        clear_future_fired(student, year, month)

def propagate_fired(student, start_year, start_month, fired_date=None):
    current_year, current_month = get_current_year_month()
    for year in range(start_year, 2027):
        start_m = start_month if year == start_year else 1
        end_m = 12 if year < current_year else current_month
        for month in range(start_m, end_m + 1):
            lbm, created = LevelByMonth.objects.get_or_create(
                student=student,
                year=year,
                month=month,
                defaults={
                    'level': 'fired',
                    'fired_date': fired_date,
                    'last_changed_at': timezone.now(),
                    'change_count': 0
                }
            )
            if not created:
                lbm.level = 'fired'
                lbm.fired_date = fired_date
                lbm.last_changed_at = timezone.now()
                lbm.save()

def clear_future_fired(student, start_year, start_month):
    current_year, current_month = get_current_year_month()
    for year in YEARS:
        start_m = start_month + 1 if year == start_year else 1
        if year < start_year:
            continue
        end_m = 12 if year < current_year else current_month
        for month in range(start_m, end_m + 1):
            lbm = LevelByMonth.objects.filter(student=student, year=year, month=month, level='fired').first()
            if lbm:
                lbm.level = ''  # Изменяем на пустую строку (Без уровня)
                lbm.fired_date = None
                lbm.save()

@receiver(pre_save, sender=Student)
def track_changes(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.only('level', 'category', 'is_called_to_hr').get(pk=instance.pk)
            instance._previous_level = old.level
            instance._previous_category = old.category
            instance._previous_is_called_to_hr = old.is_called_to_hr
        except sender.DoesNotExist:
            instance._previous_level = None
            instance._previous_category = None
            instance._previous_is_called_to_hr = False
    else:
        instance._previous_level = None
        instance._previous_category = None
        instance._previous_is_called_to_hr = False

@receiver(post_save, sender=Student)
def sync_kanban_card_and_hr_call(sender, instance, created, **kwargs):
    from apps.kanban.models import KanbanBoard, KanbanColumn, StudentKanbanCard

    # Инициализируем весь календарь (2023-2026) с "Без уровня" при создании студента
    if created:
        initialize_level_calendar(instance)

    previous_level = getattr(instance, '_previous_level', None)
    previous_category = getattr(instance, '_previous_category', None)
    previous_is_called = getattr(instance, '_previous_is_called_to_hr', False)
    is_import = getattr(instance, '_is_import', False)  # Флаг импорта

    category_changed = previous_category is not None and previous_category != instance.category
    level_changed = previous_level is not None and previous_level != instance.level
    called_changed = instance.is_called_to_hr and not previous_is_called

    # Синхронизация текущего месяца с level и fired_date студента
    if level_changed or (created and instance.level):
        update_level_by_month(
            student=instance,
            level=instance.level,
            fired_date=instance.fired_date if instance.level == 'fired' else None,
            changed_by=instance.updated_by,
            comment=getattr(instance, '_change_comment', ''),
            create_history=not is_import  # Не создаём историю при импорте
        )

    # 1. История уровней (не создаём при импорте)
    if not created and level_changed and not is_import:
        comment = getattr(instance, '_change_comment', '')
        LevelHistory.objects.create(
            student=instance,
            old_level=previous_level,
            new_level=instance.level,
            changed_by=instance.updated_by,
            comment=comment
        )
        logger.info(f"Смена уровня кота {instance.full_name}: {previous_level} → {instance.level}")

    # 2. Создание вызова к HR
    if called_changed:
        if not HrCall.objects.filter(
            student=instance,
            person_type='student',
            problem_resolved=False
        ).exists():
            HrCall.objects.create(
                person_type='student',
                student=instance,
                reason="Вызван к HR (изменение флага)",
                created_by=instance.updated_by or instance.created_by
            )
            logger.info(f"Создан вызов к HR для кота {instance.full_name}")

    # 3. Синхронизация канбан-карточки
    if instance.category in ['patriot', 'alabuga_start_rf', 'alabuga_start_sng', 'alabuga_mulatki']:
        target_board_id = "start"
    else:
        target_board_id = "polytech"

    try:
        target_board = KanbanBoard.objects.get(id=target_board_id)
    except KanbanBoard.DoesNotExist:
        logger.warning(f"Доска {target_board_id} не найдена")
        return

    target_column, _ = KanbanColumn.objects.get_or_create(
        board=target_board,
        level=instance.level or '',  
        defaults={
            'title': LEVEL_CHOICES_DICT.get(instance.level or '', 'Без уровня'),
            'color': '#9CA3AF' if instance.level == '' else '#6B7280' if instance.level == 'fired' else '#000000', 
            'position': KanbanColumn.objects.filter(board=target_board).count() + 1
        }
    )

    if category_changed:
        StudentKanbanCard.objects.filter(student=instance).delete()

    card, card_created = StudentKanbanCard.objects.update_or_create(
        student=instance,
        defaults={
            'column': target_column,
            'position': 9999
        }
    )

    category_tags = {
        'patriot': ['Патриот'],
        'alabuga_start_rf': ['Алабуга РФ'],
        'alabuga_start_sng': ['Алабуга СНГ'],
        'alabuga_mulatki': ['Алабуга МИР'],
        'college': ['Колледжист'],
    }

    current_labels = card.labels or []
    if instance.category in category_tags:
        for tag in category_tags[instance.category]:
            if tag not in current_labels:
                current_labels.append(tag)

    if card_created or sorted(card.labels or []) != sorted(current_labels):
        card.labels = current_labels
        card.save(update_fields=['labels'])

    # Очистка временных атрибутов
    for attr in ('_previous_level', '_previous_category', '_previous_is_called_to_hr', '_change_comment'):
        if hasattr(instance, attr):
            delattr(instance, attr)

    update_analytics_snapshot()

# Синхронизация изменения в календаре → student.level и fired_date (для текущего месяца)
@receiver(post_save, sender=LevelByMonth)
def sync_level_by_month_to_student(sender, instance, created, **kwargs):
    current_year, current_month = get_current_year_month()
    if instance.year == current_year and instance.month == current_month:
        # skip syncing when the entry has no level (used during initialization)
        if not instance.level:
            return
        student = instance.student
        old_level = student.level
        student.level = instance.level
        student.fired_date = instance.fired_date if instance.level == 'fired' else None
        student.save(update_fields=['level', 'fired_date'])

        # История уровней (если изменился уровень)
        if old_level != instance.level:
            LevelHistory.objects.create(
                student=student,
                old_level=old_level,
                new_level=instance.level,
                changed_by=student.updated_by,  # используем updated_by студента
                comment="Синхронизация из календаря (текущий месяц)"
            )