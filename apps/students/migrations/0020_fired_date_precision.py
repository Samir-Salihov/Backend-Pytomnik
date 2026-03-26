from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0019_alter_student_direction_alter_student_subdivision'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='fired_date_precision',
            field=models.CharField(
                blank=True,
                help_text="Используйте 'Месяц и год', если известно только месяц/год увольнения",
                null=True,
                choices=[('day', 'Точная дата'), ('month', 'Месяц и год')],
                max_length=10,
                verbose_name='Точность даты увольнения',
            ),
        ),
        migrations.AddField(
            model_name='levelbymonth',
            name='fired_date_precision',
            field=models.CharField(
                blank=True,
                null=True,
                choices=[('day', 'Точная дата'), ('month', 'Месяц и год')],
                max_length=10,
                verbose_name='Точность даты увольнения',
            ),
        ),
    ]

