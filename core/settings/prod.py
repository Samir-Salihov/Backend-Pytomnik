from .base import *
import os

DEBUG = False


ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'pytomnik'),
        'USER': os.getenv('POSTGRES_USER', 'pytomnik'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'supersecret'),
        'HOST': 'postgres',
        'PORT': 5432,
    }
}


SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'