from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db.models import Count
from django.utils import timezone
from .models import AnalyticsSnapshot
from apps.students.models import Student, LevelHistory
from apps.hr_calls.models import HrCall


def update_analytics_snapshot():
    """
    Моментальный пересчёт всей аналитики.
    """
    # Удаляем дубликаты (оставляем только id=1)
    AnalyticsSnapshot.objects.exclude(id=1).delete()

    snapshot = AnalyticsSnapshot.get_or_create_snapshot()

    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_students = Student.objects.count() or 1
    active_students = Student.objects.filter(status='active').count()
    fired_students = Student.objects.filter(status='fired').count()

    # Вызванные к HR — по открытым вызовам
    called_hr_students = HrCall.objects.filter(person_type='student', problem_resolved=False).count()

    new_students_total = Student.objects.filter(created_at__gte=current_month_start).count()
    level_changes_total = LevelHistory.objects.filter(changed_at__gte=current_month_start).count()

    # Распределение по уровням — ТОЛЬКО активные коты
    level_dist = (
        Student.objects
        .filter(status='active')
        .exclude(level='fired')
        .values('level')
        .annotate(count=Count('id'))
        .order_by('level')
    )

    # Сохраняем ТОЛЬКО количество (число!)
    distribution_by_level = {}
    for item in level_dist:
        level = item['level'] or 'Без уровня'
        distribution_by_level[level] = item['count']  # ← число, а не словарь!

    # По статусам
    status_dist = (
        Student.objects
        .values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    distribution_by_status = {
        item['status']: item['count']
        for item in status_dist
    }

    # По категориям
    category_dist = (
        Student.objects
        .values('category')
        .annotate(count=Count('id'))
        .order_by('category')
    )
    distribution_by_category = {
        (item['category'] or 'Не указано'): item['count']
        for item in category_dist
    }

    # Сохраняем
    snapshot.total_students = total_students
    snapshot.active_students = active_students
    snapshot.fired_students = fired_students
    snapshot.called_hr_students = called_hr_students
    snapshot.new_students_total = new_students_total
    snapshot.level_changes_total = level_changes_total
    snapshot.distribution_by_level = distribution_by_level
    snapshot.distribution_by_status = distribution_by_status
    snapshot.distribution_by_category = distribution_by_category

    snapshot.save(update_fields=[
        'total_students', 'active_students', 'fired_students', 'called_hr_students',
        'new_students_total', 'level_changes_total',
        'distribution_by_level', 'distribution_by_status', 'distribution_by_category'
    ])


def reset_monthly_counters_if_needed():
    snapshot = AnalyticsSnapshot.get_or_create_snapshot()
    now = timezone.now()

    if snapshot.updated_at.month != now.month or snapshot.updated_at.year != now.year:
        snapshot.new_students_total = 0
        snapshot.level_changes_total = 0
        snapshot.save(update_fields=['new_students_total', 'level_changes_total'])


@receiver([post_save, pre_delete], sender=Student)
def update_on_student_change(sender, instance, **kwargs):
    update_analytics_snapshot()
    reset_monthly_counters_if_needed()


@receiver(post_save, sender=LevelHistory)
def update_on_level_history_create(sender, instance, created, **kwargs):
    if created:
        snapshot = AnalyticsSnapshot.get_or_create_snapshot()
        snapshot.level_changes_total += 1
        snapshot.save(update_fields=['level_changes_total'])
    update_analytics_snapshot()
    reset_monthly_counters_if_needed()


@receiver(pre_delete, sender=LevelHistory)
def update_on_level_history_delete(sender, instance, **kwargs):
    snapshot = AnalyticsSnapshot.get_or_create_snapshot()
    if snapshot.level_changes_total > 0:
        snapshot.level_changes_total -= 1
        snapshot.save(update_fields=['level_changes_total'])
    update_analytics_snapshot()


@receiver(post_save, sender=HrCall)
def update_on_hr_call_change(sender, instance, created, **kwargs):
    if created and instance.person_type == 'student':
        update_analytics_snapshot()
        reset_monthly_counters_if_needed()


@receiver(pre_delete, sender=HrCall)
def update_on_hr_call_delete(sender, instance, **kwargs):
    if instance.person_type == 'student':
        update_analytics_snapshot()