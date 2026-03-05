from .base import *
import os

DEBUG = False


ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'pytomnic'),
        'USER': os.getenv('POSTGRES_USER', 'pytomnic_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'pytomnic123'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}


SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Redis Cache Settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Session Engine
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# S3 Storage settings
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ru-msk')
AWS_S3_SIGNATURE_VERSION = os.getenv('AWS_S3_SIGNATURE_VERSION', 's3v4')
AWS_S3_ADDRESSING_STYLE = os.getenv('AWS_S3_ADDRESSING_STYLE', 'path')
AWS_LOCATION = os.getenv('AWS_LOCATION', 'media')

DEFAULT_FILE_STORAGE = os.getenv('DEFAULT_FILE_STORAGE', 'storages.backends.s3boto3.S3Boto3Storage')
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
AWS_S3_OBJECT_PARAMETERS = {"ACL": "public-read"}
AWS_S3_OBJECT_PARAMETERS = {"ACL": "public-read"}

# Временно отключаем S3
# DEFAULT_FILE_STORAGE = os.getenv('DEFAULT_FILE_STORAGE', 'storages.backends.s3boto3.S3Boto3Storage')
# MEDIA_URL = os.getenv('MEDIA_URL', '/media/')

# Используем локальное хранилище
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = '/app/media'
CSRF_TRUSTED_ORIGINS = ["https://al-pytomnic.ru", "http://al-pytomnic.ru"]
