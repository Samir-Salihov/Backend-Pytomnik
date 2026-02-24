# apps/export/tasks.py
from celery import shared_task
from .services import generate_excel_stream
from django.conf import settings
import os
from datetime import timezone

@shared_task
def async_export_excel():
    wb = generate_excel_stream()
    # use generic export_data prefix rather than referencing students
    filename = f"export_data_{timezone.now():%Y%m%d_%H%M%S}.xlsx"
    path = os.path.join(settings.MEDIA_ROOT, "exports", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    return f"/media/exports/{filename}"