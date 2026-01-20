from django.apps import AppConfig


class HrCallsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hr_calls'
    verbose_name = "Вызовы к HR"

    def ready(self):
        # Импорт сигналов при запуске приложения
        import apps.hr_calls.signals