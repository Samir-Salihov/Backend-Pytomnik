"""
Валидаторы для полей моделей и сериализаторов
Централизованное место для всех функций валидации
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import re
from utils.exceptions import (
    InvalidPhoneException,
    PhoneInvalidFormatException,
    PhoneTooLongException,
    InvalidAgeException,
    AgeExceedsLimitException,
    InvalidYearException,
    InvalidBirthDateException,
    InvalidNameException,
)


# ============================================================================
# ВАЛИДАТОРЫ ТЕЛЕФОНОВ
# ============================================================================

def validate_phone_number(phone):
    """
    Валидирует номер телефона:
    - Должен содержать только цифры
    - Максимально 11 символов
    - Не может быть пустым
    """
    if not phone:
        return  # Поле может быть опциональным
    
    # Убираем пробелы, тире, скобки и другие символы
    phone_clean = ''.join(filter(str.isdigit, str(phone)))
    
    # Проверяем, что строка содержит только допустимые символы.
    # Разрешаем стандартные форматы вроде "+7 (999) 111-22-33".
    s = str(phone).strip()
    allowed_chars = set("0123456789 -()+")
    if any(c not in allowed_chars for c in s):
        raise ValidationError("Номер телефона содержит недопустимые символы")

    # Разрешаем "+" только один раз и только в начале
    if "+" in s and not s.startswith("+"):
        raise ValidationError("Символ '+' допустим только в начале номера")
    if s.count("+") > 1:
        raise ValidationError("В номере телефона может быть только один символ '+'")
    
    # Проверяем длину (только цифры)
    if len(phone_clean) > 11:
        raise ValidationError(f"Номер телефона не должен превышать 11 цифр (введено: {len(phone_clean)})")
    
    # Должно быть хотя бы несколько цифр
    if len(phone_clean) < 7:
        raise ValidationError("Номер телефона должен содержать минимум 7 цифр")


def validate_phone_digits_only(phone):
    """
    Валидирует, что номер телефона содержит только цифры
    """
    if not phone:
        return
    
    if not str(phone).isdigit():
        raise ValidationError("Номер телефона должен содержать только цифры")
    
    if len(str(phone)) > 11:
        raise ValidationError(f"Номер телефона не должен превышать 11 цифр (введено: {len(str(phone))})")


# ============================================================================
# ВАЛИДАТОРЫ ВОЗРАСТА И ДАТ
# ============================================================================

def validate_birth_date(birth_date):
    """
    Валидирует дату рождения:
    - Не может быть в будущем
    - Возраст должен быть от 14 до 30 лет
    """
    if not birth_date:
        return
    
    today = timezone.now().date()
    
    # Проверка, что дата не в будущем
    if birth_date > today:
        raise InvalidBirthDateException(
            "Дата рождения не может быть в будущем"
        )
    
    # Расчет возраста
    delta = relativedelta(today, birth_date)
    age = delta.years
    
    # Проверка возраста
    if age < 14:
        raise InvalidAgeException(
            f"Возраст должен быть от 14 лет (сейчас: {age})"
        )
    
    if age > 30:
        raise AgeExceedsLimitException(
            f"Возраст не может быть больше 30 лет (сейчас: {age})"
        )


def calculate_age(birth_date):
    """
    Расчитывает возраст на основе даты рождения
    Возвращает None если дата рождения не указана
    """
    if not birth_date:
        return None
    
    today = timezone.now().date()
    delta = relativedelta(today, birth_date)
    return delta.years


def validate_age(age):
    """
    Валидирует возраст:
    - От 14 до 30 лет
    """
    if age is None:
        return
    
    age = int(age)
    if age < 14:
        raise InvalidAgeException("Возраст должен быть от 14 лет")
    
    if age > 30:
        raise AgeExceedsLimitException("Возраст не может быть больше 30 лет")


def validate_year(year):
    """
    Валидирует год:
    - Не может быть больше текущего года
    """
    if not year:
        return
    
    current_year = timezone.now().year
    year = int(year)
    
    if year > current_year:
        raise InvalidYearException(
            f"Год не может быть больше {current_year}"
        )


def validate_future_year(year):
    """
    Валидирует год для будущих дат:
    - Может быть равен или больше текущего года
    """
    if not year:
        return
    
    current_year = timezone.now().year
    year = int(year)
    
    if year < current_year - 50:  # Защита от очень старых годов
        raise ValidationError(
            f"Год не может быть раньше {current_year - 50}"
        )


# ============================================================================
# ВАЛИДАТОРЫ ИМЕН
# ============================================================================

def validate_name(name, field_name="Имя"):
    """
    Валидирует имя:
    - Не может быть пустым
    - Не может быть очень длинным
    - Должно содержать корректные символы
    """
    if not name or not str(name).strip():
        raise InvalidNameException(
            f"{field_name} не может быть пустым"
        )
    
    name = str(name).strip()
    
    # Проверка длины
    if len(name) > 100:
        raise InvalidNameException(
            f"{field_name} не может быть длиннее 100 символов"
        )
    
    # Проверка минимальной длины
    if len(name) < 2:
        raise InvalidNameException(
            f"{field_name} должно содержать минимум 2 символа"
        )
    
    # Проверка корректных символов (буквы, пробелы, дефисы, апострофы)
    if not re.match(r"^[а-яёА-ЯЁa-zA-Z\s\-'ʼ]+$", name):
        raise InvalidNameException(
            f"{field_name} содержит недопустимые символы"
        )


def validate_first_name(first_name):
    """Валидирует имя"""
    validate_name(first_name, "Имя")


def validate_last_name(last_name):
    """Валидирует фамилию"""
    validate_name(last_name, "Фамилия")


def validate_patronymic(patronymic):
    """Валидирует отчество (опциональное поле)"""
    if patronymic:
        validate_name(patronymic, "Отчество")


# ============================================================================
# ВАЛИДАТОРЫ ТЕКСТА
# ============================================================================

def validate_text_field(text, field_name="Текст", max_length=None, min_length=None):
    """
    Валидирует текстовое поле
    """
    if not text:
        return
    
    text = str(text).strip()
    
    if min_length and len(text) < min_length:
        raise ValidationError(
            f"{field_name} должно содержать минимум {min_length} символов"
        )
    
    if max_length and len(text) > max_length:
        raise ValidationError(
            f"{field_name} не может быть длиннее {max_length} символов"
        )


def validate_reason_field(reason):
    """Валидирует поле причины"""
    validate_text_field(reason, "Причина", min_length=5, max_length=1000)


def validate_solution_field(solution):
    """Валидирует поле решения"""
    validate_text_field(solution, "Решение", min_length=5, max_length=1000)


# ============================================================================
# ВАЛИДАТОРЫ ДЛЯ DATETIME
# ============================================================================

def validate_datetime_not_future(datetime_value):
    """
    Валидирует, что дата и время не в будущем
    """
    if not datetime_value:
        return
    
    now = timezone.now()
    if datetime_value > now:
        raise ValidationError(
            "Дата и время не может быть в будущем"
        )


def validate_datetime_in_range(datetime_value, max_days_ago=365):
    """
    Валидирует, что дата и время в разумном диапазоне
    """
    if not datetime_value:
        return
    
    now = timezone.now()
    min_date = now - timezone.timedelta(days=max_days_ago)
    
    if datetime_value < min_date:
        raise ValidationError(
            f"Дата не может быть раньше чем {max_days_ago} дней назад"
        )
    
    if datetime_value > now:
        raise ValidationError(
            "Дата и время не может быть в будущем"
        )


# ============================================================================
# ВАЛИДАТОРЫ ENUM/CHOICES
# ============================================================================

def validate_choice(value, choices, field_name="Поле"):
    """
    Валидирует, что значение находится в списке доступных опций
    
    Args:
        value: Проверяемое значение
        choices: Список доступных значений или список кортежей (value, display_name)
        field_name: Название поля для сообщения об ошибке
    """
    if not value:
        return
    
    # Если choices это список кортежей (как в Django choices)
    if choices and isinstance(choices[0], (list, tuple)):
        allowed_values = [choice[0] for choice in choices]
    else:
        allowed_values = list(choices)
    
    if value not in allowed_values:
        raise ValidationError(
            f"{field_name} должен быть одним из: {', '.join(str(x) for x in allowed_values)}"
        )


# ============================================================================
# ВАЛИДАТОРЫ ЧИСЛОВЫХ ПОЛЕЙ
# ============================================================================

def validate_positive_integer(value, field_name="Число"):
    """Валидирует положительное целое число"""
    if value is None:
        return
    
    try:
        num = int(value)
        if num < 0:
            raise ValidationError(
                f"{field_name} должно быть положительным числом"
            )
    except (ValueError, TypeError):
        raise ValidationError(
            f"{field_name} должно быть целым числом"
        )


def validate_decimal_range(value, min_value=0, max_value=100, field_name="Число"):
    """Валидирует десятичное число в диапазоне"""
    if value is None:
        return
    
    try:
        num = float(value)
        if num < min_value or num > max_value:
            raise ValidationError(
                f"{field_name} должно быть между {min_value} и {max_value}"
            )
    except (ValueError, TypeError):
        raise ValidationError(
            f"{field_name} должно быть числом"
        )


# ============================================================================
# ВАЛИДАТОРЫ ФАЙЛОВ
# ============================================================================

def validate_file_size(file, max_size_mb=10):
    """
    Originally this function enforced a maximum upload size.  the project
    no longer applies any such limits for photo uploads, so it has been
    reduced to a no-op.  It remains here only for historical compatibility
    (calls that might be added by third-party code).

    Args:
        file: File object (ignored)
        max_size_mb: Maximum size in megabytes (ignored)
    """
    # intentionally do nothing
    return


def validate_file_extension(file, allowed_extensions):
    """
    Previously used to restrict uploaded file extensions.  we no longer
    impose any extension restrictions on photos or other uploads, so this
    validator has been turned into a pass-through.
    """
    return


# ============================================================================
# КОМБИНИРОВАННЫЕ ВАЛИДАТОРЫ
# ============================================================================

def validate_student_data(data):
    """
    Комбинированная валидация данных студента
    """
    errors = {}
    
    # Проверка имён
    try:
        if data.get('first_name'):
            validate_first_name(data['first_name'])
    except ValidationError as e:
        errors['first_name'] = str(e.message)
    
    try:
        if data.get('last_name'):
            validate_last_name(data['last_name'])
    except ValidationError as e:
        errors['last_name'] = str(e.message)
    
    try:
        if data.get('patronymic'):
            validate_patronymic(data['patronymic'])
    except ValidationError as e:
        errors['patronymic'] = str(e.message)
    
    # Проверка дня рождения
    try:
        if data.get('birth_date'):
            validate_birth_date(data['birth_date'])
    except ValidationError as e:
        errors['birth_date'] = str(e.message)
    
    # Проверка телефонов
    try:
        if data.get('phone_personal'):
            validate_phone_number(data['phone_personal'])
    except Exception as e:
        errors['phone_personal'] = str(e)
    
    try:
        if data.get('phone_parent'):
            validate_phone_number(data['phone_parent'])
    except Exception as e:
        errors['phone_parent'] = str(e)
    
    if errors:
        raise ValidationError(errors)
