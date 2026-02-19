from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Local Development Settings
# Check if we should use SQLite (default for local runs unless configured otherwise)
USE_SQLITE = os.getenv('USE_SQLITE', 'True') == 'True'

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'pytomnic',
            'USER': 'pytomnic_user',
            'PASSWORD': 'pytomnic123',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE