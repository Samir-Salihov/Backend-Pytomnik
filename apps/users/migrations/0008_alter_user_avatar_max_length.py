# Manual migration to bump avatar max_length to 1000
from django.db import migrations, models
from apps.users.models import user_avatar_upload_path


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_alter_user_is_staff'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, help_text='Рекомендуемый размер: 300x300 пикселей', max_length=1000, null=True, upload_to=user_avatar_upload_path, verbose_name='Аватар'),
        ),
    ]
