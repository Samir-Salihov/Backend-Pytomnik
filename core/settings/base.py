"""
Основные настройки проекта — общие для dev и prod
"""
from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.management.utils import get_random_secret_key
from datetime import timedelta, time

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY') or get_random_secret_key()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = False

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'django_filters',
    'channels',
    'whitenoise.runserver_nostatic',
    'rest_framework_simplejwt',

    'apps.students',
    'apps.analytics',
    'apps.users',
    'corsheaders',
    'apps.kanban',
    'apps.export',
    'apps.hr_calls',

    'jazzmin',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
ASGI_APPLICATION = 'core.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# core/settings/base.py

BASE_DIR = Path(__file__).resolve().parent.parent

# По умолчанию — SQLite (для разработки)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC' 
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'


CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('localhost', 6379)],
        },
    },
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'apps.users.exceptions.custom_exception_handler',
} 

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
}
 
AUTH_USER_MODEL = "users.User"


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}


ALLOWED_HOSTS = ["*"]


CORS_ALLOW_ALL_ORIGINS = True






# Настройки для экспорта
EXPORT_SETTINGS = {
    'MAX_SYNC_EXPORT': 5000,           # Максимум записей для синхронного экспорта
    'EXPORT_FILE_TTL_DAYS': 7,         # Хранить файлы 7 дней
    'LOG_RETENTION_DAYS': 30,          # Хранить логи 30 дней
    'STORAGE_PATH': os.path.join(MEDIA_ROOT, 'exports'),
    'DEFAULT_PAGE_SIZE': 20,           # Размер страницы по умолчанию
}


# Периодические задачи Celery (Beat)
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-exports-daily': {
        'task': 'export_excel.tasks.cleanup_old_exports',
        'schedule': 86400.0,  # Каждые 24 часа
        'options': {
            'expires': 3600,
        }
    },
    'generate-export-summary-daily': {
        'task': 'export_excel.tasks.generate_export_summary',
        'schedule': 86400.0,  
        'options': {
            'eta': time(23, 59, 0),
            'expires': 3600,
        }
    },
    'cleanup-old-logs-weekly': {
        'task': 'export_excel.tasks.cleanup_old_logs_task',
        'schedule': 7 * 86400.0,  
        'args': (30,),
        'options': {
            'expires': 3600,
        }
    },
    'export-statistics-report-weekly': {
        'task': 'export_excel.tasks.export_statistics_report',
        'schedule': 7 * 86400.0,  
        'options': {
            'expires': 3600,
        }
    },
}


JAZZMIN_SETTINGS = {
    "site_title": "Питомник Алабуга",
    "site_header": "Питомник Алабуга",
    "site_brand": "Питомник",
    "welcome_sign": "Добро пожаловать в аналитику Питомника",
    "copyright": "Алабуга Старт & Политех 2026",
    "search_model": ["students.Student", "kanban.KanbanBoard"],
    "topmenu_links": [
        {"name": "Дашборд", "url": "admin:analytics_dashboard", "permissions": ["is_staff"]},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "analytics": "fas fa-chart-line",
        "students": "fas fa-users",
        "kanban": "fas fa-columns",
    },
    "default_ui_tweaks": {
        "sidebar_nav_small_text": False,
        "accent": "accent-primary",
        "navbar": "navbar-dark",
        "no_navbar_border": False,
        "navbar_fixed": True,
        "layout_boxed": False,
        "footer_fixed": False,
        "sidebar_fixed": True,
        "sidebar_collapse": False,
        "sidebar_collapse_on_scroll": True,
    }
}