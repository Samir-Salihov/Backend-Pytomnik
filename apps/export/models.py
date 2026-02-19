from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ExportLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    exported_at = models.DateTimeField("Дата и время выгрузки", default=timezone.now)
    format = models.CharField("Формат", max_length=10, choices=[('excel', 'Excel'), ('csv', 'CSV')])
    students_count = models.PositiveIntegerField("Количество колледжистов")

    class Meta:
        app_label = 'export'
        verbose_name = "Лог выгрузки"
        verbose_name_plural = "Логи выгрузок"
        ordering = ['-exported_at']

    def __str__(self):
        return f"{self.user} — {self.format.upper()} — {self.students_count} колледжистов — {self.exported_at.strftime('%d.%m.%Y %H:%M')}" 