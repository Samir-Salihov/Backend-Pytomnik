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

@receiver(post_save, sender=HrCall)
def update_student_hr_status(sender, instance, **kwargs):
    if instance.problem_resolved and instance.person_type == 'student' and instance.student:
        instance.student.is_called_to_hr = False
        instance.student.save(update_fields=['is_called_to_hr'])