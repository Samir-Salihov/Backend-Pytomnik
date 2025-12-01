# core/settings/__init__.py
from .base import *
import os
from dotenv import load_dotenv

# Определяем, в каком режиме мы
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')  # development или production

if ENVIRONMENT == 'production':
    from .prod import *
else:
    from .dev import *