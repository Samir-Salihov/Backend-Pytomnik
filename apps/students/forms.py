from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
import re


class PartialDateField(forms.DateField):
    """
    Поле для ввода даты увольнения с автоматическим определением точности.
    Поддерживает форматы:
    - День: 01.01.2025, 01/01/2025, 2025-01-01
    - Месяц: 01.2025, 01/2025, 2025-01, Январь 2025
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('input_formats', [
            '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d',  # Полные даты
            '%m.%Y', '%m/%Y', '%Y-%m',           # Только месяц и год
        ])
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        if value in self.empty_values:
            return None
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            value = value.strip()
            
            # Проверяем формат "Месяц Год" (например, "Январь 2025")
            month_year_pattern = r'^(январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь)\s+(\d{4})$'
            match = re.match(month_year_pattern, value.lower())
            if match:
                months = {
                    'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4,
                    'май': 5, 'июнь': 6, 'июль': 7, 'август': 8,
                    'сентябрь': 9, 'октябрь': 10, 'ноябрь': 11, 'декабрь': 12
                }
                month_name = match.group(1)
                year = int(match.group(2))
                month = months[month_name]
                return datetime(year, month, 1).date()
            
            # Проверяем формат "Месяц.Год" или "Месяц/Год" или "Год-Месяц"
            month_year_simple = r'^(\d{1,2})[./-](\d{4})$|^(\d{4})[./-](\d{1,2})$'
            match = re.match(month_year_simple, value)
            if match:
                if match.group(1) and match.group(2):  # ММ.ГГГГ или ММ/ГГГГ
                    month = int(match.group(1))
                    year = int(match.group(2))
                else:  # ГГГГ-ММ
                    year = int(match.group(3))
                    month = int(match.group(4))
                
                if 1 <= month <= 12 and 1900 <= year <= 2100:
                    return datetime(year, month, 1).date()
                else:
                    raise ValidationError('Некорректная дата. Месяц должен быть от 1 до 12, год от 1900 до 2100.')
            
            # Пытаемся распарсить как полную дату
            for fmt in self.input_formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.date()
                except ValueError:
                    continue
        
        raise ValidationError('Введите корректную дату в формате ДД.ММ.ГГГГ, ММ.ГГГГ или "Месяц Год".')

    def prepare_value(self, value):
        """Преобразует значение для отображения в форме"""
        if isinstance(value, datetime):
            value = value.date()
        
        if isinstance(value, str):
            # Если это уже строка, возвращаем как есть
            return value
        
        if value is None:
            return ''
        
        # Автоматическое определение точности для отображения
        if value.day == 1:
            # Точность "месяц"
            months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
            return f"{months_ru[value.month - 1]} {value.year}"
        else:
            # Точность "день"
            return value.strftime('%d.%m.%Y')