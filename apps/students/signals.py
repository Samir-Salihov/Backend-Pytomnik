from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import Student, LevelHistory, LevelByMonth
from apps.analytics.signals import update_analytics_snapshot

logger = logging.getLogger(__name__)

LEVEL_CHOICES_DICT = dict([
    ('black', 'Чёрный уровень'),
    ('red', 'Красный уровень'),
    ('yellow', 'Жёлтый уровень'),
    ('green', 'Зелёный уровень'),
    ('fired', 'Уволен'),
])

YEARS = range(2023, 2027)

def get_current_year_month():
    now = timezone.now()
    return now.year, now.month

def update_level_by_month(student, level, fired_date=None, changed_by=None, comment=''):
    year, month = get_current_year_month()

    # Создаём запись в LevelHistory
    old_level = student.level
    if old_level != level:
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

def propagate_fired(student, start_year, start_month, fired_date):
    current_year, current_month = get_current_year_month()
    for year in YEARS:
        start_m = start_month if year == start_year else 1
        end_m = 12 if year < current_year else current_month
        for month in range(start_m, end_m + 1):
            LevelByMonth.objects.update_or_create(
                student=student,
                year=year,
                month=month,
                defaults={
                    'level': 'fired',
                    'fired_date': fired_date,
                    'last_changed_at': timezone.now(),
                    'change_count': LevelByMonth.objects.filter(student=student, year=year, month=month).first().change_count or 0
                }
            )

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
                lbm.level = None
                lbm.fired_date = None
                lbm.save()

@receiver(pre_save, sender=Student)
def track_level_and_category_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.only('level', 'category').get(pk=instance.pk)
            instance._previous_level = old.level
            instance._previous_category = old.category
        except sender.DoesNotExist:
            instance._previous_level = None
            instance._previous_category = None
    else:
        instance._previous_level = None
        instance._previous_category = None

@receiver(post_save, sender=Student)
def sync_kanban_card(sender, instance, created, **kwargs):
    from apps.kanban.models import KanbanBoard, KanbanColumn, StudentKanbanCard

    previous_level = getattr(instance, '_previous_level', None)
    previous_category = getattr(instance, '_previous_category', None)

    category_changed = previous_category is not None and previous_category != instance.category
    level_changed = previous_level is not None and previous_level != instance.level

    if level_changed or created:
        update_level_by_month(
            student=instance,
            level=instance.level,
            fired_date=instance.fired_date if instance.level == 'fired' else None,
            changed_by=instance.updated_by,
            comment=getattr(instance, '_change_comment', '')
        )

    # ... остальная логика канбана (доска, колонка, карточка, теги) остается как была ...

    # (оставляю твою логику доски, колонки, карточки, тегов без изменений)

    # Очистка временных атрибутов
    for attr in ('_previous_level', '_previous_category', '_change_comment'):
        if hasattr(instance, attr):
            delattr(instance, attr)

    update_analytics_snapshot()