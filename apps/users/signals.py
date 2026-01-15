# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import User

# @receiver(post_save, sender=User)
# def assign_super_admin_role(sender, instance, created, **kwargs):
#     """
#     Автоматически назначаем роль 'super_admin' первому суперюзеру, созданному через createsuperuser.
#     """
#     if created and instance.is_superuser:
#         # Проверяем, что это первый суперюзер с ролью super_admin
#         if not User.objects.filter(role='super_admin').exists():
#             instance.role = 'super_admin'
#             instance.save(update_fields=['role'])
#             print(f"Роль 'super_admin' автоматически назначена пользователю {instance.username}.")