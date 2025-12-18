# celery.py
import os
from celery_app import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('pytomnik')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()