from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import logging

from apps.students.models import Student
from .models import HrCall

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Student)
def track_status_change(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.only('status').get(pk=instance.pk)
        instance._previous_status = old.status
    else:
        instance._previous_status = None


@receiver(post_save, sender=Student)
def cleanup_previous_status(sender, instance, **kwargs):
    if hasattr(instance, '_previous_status'):
        delattr(instance, '_previous_status')

@receiver(pre_save, sender=HrCall)
def track_hr_call_changes(sender, instance, **kwargs):
    if instance.pk:
        old_instance = HrCall.objects.only('problem_resolved').get(pk=instance.pk)
        instance._old_problem_resolved = old_instance.problem_resolved
    else:
        instance._old_problem_resolved = False

@receiver(post_save, sender=HrCall)
def update_student_hr_status(sender, instance, **kwargs):
    # ВСЕГДА сбрасываем флаг если проблема отмечена как решена
    # Работает при создании и при редактировании
    if instance.problem_resolved:
        if instance.person_type == 'student' and instance.student:
            if instance.student.is_called_to_hr:
                instance.student.is_called_to_hr = False
                instance.student.save(update_fields=['is_called_to_hr'])
