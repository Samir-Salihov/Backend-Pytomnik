from django.db import models


class Analytics(models.Model):
    """Модель для кнопки аналитики в админке"""
    
    class Meta:
        verbose_name = 'Analytics'
        verbose_name_plural = 'Analytics'
        # Скрываем модель из списка моделей в админке
        default_permissions = ()
        permissions = [
            ("can_view_analytics", "Can view analytics dashboard"),
        ]