from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr_calls', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='hrcall',
            name='category',
            field=models.CharField(blank=True, help_text="Категория кота (Колледжисты/АС(СНГ)/АС(РФ)/АС(МИР)/Патриоты) или пусто для 'Не кот'", max_length=50, verbose_name='Категория'),
        ),
        migrations.AlterField(
            model_name='hrcall',
            name='person_type',
            field=models.CharField(choices=[('cat', 'Кот'), ('not_cat', 'Не кот')], help_text='Кот или обычный человек', max_length=20, verbose_name='Тип человека'),
        ),
    ]

