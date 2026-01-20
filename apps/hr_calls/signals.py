from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import logging

from apps.students.models import Student
from .models import HrCall
from apps.analytics.signals import update_analytics_snapshot

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Student)
def track_status_change_and_create_hr(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.only('status').get(pk=instance.pk)
        instance._previous_status = old.status

        # Создаём HrCall ТОЛЬКО если статус меняется на called_hr и записи ещё нет
        if old.status != 'called_hr' and instance.status == 'called_hr':
            if not HrCall.objects.filter(student=instance, person_type='student').exists():
                HrCall.objects.create(
                    person_type='student',
                    student=instance,
                    reason="",  # пустая причина
                    created_by=instance.updated_by
                )
                logger.info(f"Создан вызов к HR для кота {instance.full_name}")
    else:
        instance._previous_status = None


@receiver(post_save, sender=Student)
def cleanup_previous_status(sender, instance, **kwargs):
    # Только очистка временного атрибута
    if hasattr(instance, '_previous_status'):
        delattr(instance, '_previous_status')
    update_analytics_snapshot()