# migration to increase max_length on file fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0017_alter_student_photo_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medicalfile',
            name='file',
            field=models.FileField(max_length=1000, upload_to='students/medical_files/', verbose_name='Медицинский файл'),
        ),
        migrations.AlterField(
            model_name='violationact',
            name='file',
            field=models.FileField(blank=True, null=True, max_length=1000, upload_to='students/violation_acts/', verbose_name='Файл'),
        ),
    ]
