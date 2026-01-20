from django.db import models
from django.utils import timezone
from django.db.models import Q


class AnalyticsSnapshot(models.Model):
    """
    Единая запись с текущей аналитикой.
    Обновляется сигналами моментально.
    new_students_total и level_changes_total — за текущий месяц.
    """
    total_students = models.PositiveIntegerField("Всего котов", default=0)
    active_students = models.PositiveIntegerField("Активные", default=0)
    fired_students = models.PositiveIntegerField("Уволенные", default=0)
    called_hr_students = models.PositiveIntegerField("Вызванные к HR (коты)", default=0)

    new_students_total = models.PositiveIntegerField("Новые коты (текущий месяц)", default=0)
    level_changes_total = models.PositiveIntegerField("Изменения уровня (текущий месяц)", default=0)

    distribution_by_level = models.JSONField("Распределение по уровням", default=dict)
    distribution_by_status = models.JSONField("Распределение по статусам", default=dict)
    distribution_by_category = models.JSONField("Распределение по категориям", default=dict)

    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Снимок аналитики"
        verbose_name_plural = "Снимки аналитики"

    def __str__(self):
        return f"Аналитика на {self.updated_at.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_or_create_snapshot(cls):
        snapshot, _ = cls.objects.get_or_create(id=1)
        return snapshot

    def reset_monthly_counters(self):
        """
        Сбрасывает счётчики за месяц (вызывается 1-го числа)
        """
        self.new_students_total = 0
        self.level_changes_total = 0
        self.save(update_fields=['new_students_total', 'level_changes_total'])