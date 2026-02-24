# Generated manually to increase photo max_length
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0016_alter_comment_options_alter_student_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='photo',
            field=models.ImageField(max_length=1000, upload_to='students/photos/', null=True, blank=True, verbose_name='Фото колледжиста'),
        ),
    ]
