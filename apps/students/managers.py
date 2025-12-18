# apps/students/managers.py
from django.db import models


class StudentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status='active')

    def by_level(self, level):
        return self.filter(level=level)

    def with_full_name(self):
        from django.db.models.functions import Concat
        from django.db.models import Value as V
        return self.annotate(full_name=Concat('last_name', V(' '), 'first_name', V(' '), 'patronymic'))

class StudentManager(models.Manager.from_queryset(StudentQuerySet)):
    pass