"""
Централизованная система обработки исключений и валидации для всего API
Все custom exceptions определяются здесь для ясности и консистентности
"""

from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError


# ============================================================================
# БАЗОВЫЕ CUSTOM EXCEPTIONS
# ============================================================================

class APIException(Exception):
    """Базовый класс для всех API исключений"""
    def __init__(self, message="Ошибка при обработке запроса", code=None, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code or self.__class__.__name__
        self.status_code = status_code
        super().__init__(self.message)


# ============================================================================
# ИСКЛЮЧЕНИЯ АУТЕНТИФИКАЦИИ И АВТОРИЗАЦИИ
# ============================================================================

class InvalidCredentialsException(APIException):
    """Неверные учетные данные для входа"""
    def __init__(self, message="Неверный логин или пароль"):
        super().__init__(message, "INVALID_CREDENTIALS", status.HTTP_401_UNAUTHORIZED)


class UnauthorizedException(APIException):
    """Пользователь не аутентифицирован"""
    def __init__(self, message="Требуется аутентификация"):
        super().__init__(message, "UNAUTHORIZED", status.HTTP_401_UNAUTHORIZED)


class AccessDeniedException(APIException):
    """Доступ к ресурсу запрещен"""
    def __init__(self, message="У вас нет прав для этого действия"):
        super().__init__(message, "ACCESS_DENIED", status.HTTP_403_FORBIDDEN)


class PermissionDeniedException(APIException):
    """Недостаточно прав для выполнения операции"""
    def __init__(self, message="Доступ запрещён"):
        super().__init__(message, "PERMISSION_DENIED", status.HTTP_403_FORBIDDEN)


# ============================================================================
# ИСКЛЮЧЕНИЯ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

class UserException(APIException):
    """Базовое исключение для операций с пользователями"""
    pass


class UserNotFoundException(UserException):
    """Пользователь не найден"""
    def __init__(self, message="Пользователь не найден"):
        super().__init__(message, "USER_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class UserAlreadyExistsException(UserException):
    """Пользователь с таким логином/email уже существует"""
    def __init__(self, message="Пользователь с таким логином или email уже существует"):
        super().__init__(message, "USER_ALREADY_EXISTS", status.HTTP_400_BAD_REQUEST)


class InvalidUsernameException(UserException):
    """Неверный формат логина"""
    def __init__(self, message="Логин должен содержать от 3 до 50 символов"):
        super().__init__(message, "INVALID_USERNAME", status.HTTP_400_BAD_REQUEST)


class InvalidPasswordException(UserException):
    """Неверный формат пароля"""
    def __init__(self, message="Пароль не соответствует требованиям безопасности"):
        super().__init__(message, "INVALID_PASSWORD", status.HTTP_400_BAD_REQUEST)


class PasswordMismatchException(UserException):
    """Пароли не совпадают"""
    def __init__(self, message="Пароли не совпадают"):
        super().__init__(message, "PASSWORD_MISMATCH", status.HTTP_400_BAD_REQUEST)


class InvalidEmailException(UserException):
    """Неверный формат email"""
    def __init__(self, message="Неверный формат email"):
        super().__init__(message, "INVALID_EMAIL", status.HTTP_400_BAD_REQUEST)


class InvalidTelegramException(UserException):
    """Неверный формат Telegram username"""
    def __init__(self, message="Имя пользователя Telegram должно содержать только латинские буквы, цифры и подчеркивания (5-32 символа)"):
        super().__init__(message, "INVALID_TELEGRAM", status.HTTP_400_BAD_REQUEST)


class MissingContactInfoException(UserException):
    """Отсутствует контактная информация"""
    def __init__(self, message="Укажите email или Telegram для связи"):
        super().__init__(message, "MISSING_CONTACT_INFO", status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ИСКЛЮЧЕНИЯ СТУДЕНТОВ
# ============================================================================

class StudentException(APIException):
    """Базовое исключение для операций со студентами"""
    pass


class StudentNotFoundException(StudentException):
    """Студент не найден"""
    def __init__(self, message="Студент не найден"):
        super().__init__(message, "STUDENT_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class InvalidAgeException(StudentException):
    """Неверный возраст студента"""
    def __init__(self, message="Возраст должен быть от 14 до 30 лет"):
        super().__init__(message, "INVALID_AGE", status.HTTP_400_BAD_REQUEST)


class AgeExceedsLimitException(StudentException):
    """Возраст превышает максимальный лимит"""
    def __init__(self, message="Возраст не может быть больше 30 лет"):
        super().__init__(message, "AGE_EXCEEDS_LIMIT", status.HTTP_400_BAD_REQUEST)


class InvalidPhoneException(StudentException):
    """Неверный формат телефона"""
    def __init__(self, message="Номер телефона должен содержать только цифры и иметь длину не более 11 символов"):
        super().__init__(message, "INVALID_PHONE", status.HTTP_400_BAD_REQUEST)


class PhoneInvalidFormatException(StudentException):
    """Телефон содержит недопустимые символы"""
    def __init__(self, message="Номер телефона должен содержать только цифры"):
        super().__init__(message, "PHONE_INVALID_FORMAT", status.HTTP_400_BAD_REQUEST)


class PhoneTooLongException(StudentException):
    """Номер телефона слишком длинный"""
    def __init__(self, message="Номер телефона не должен превышать 11 цифр"):
        super().__init__(message, "PHONE_TOO_LONG", status.HTTP_400_BAD_REQUEST)


class InvalidNameException(StudentException):
    """Неверный формат имени"""
    def __init__(self, message="Имя должно быть непустым и содержать корректные символы"):
        super().__init__(message, "INVALID_NAME", status.HTTP_400_BAD_REQUEST)


class InvalidBirthDateException(StudentException):
    """Неверная дата рождения"""
    def __init__(self, message="Дата рождения не может быть в будущем"):
        super().__init__(message, "INVALID_BIRTH_DATE", status.HTTP_400_BAD_REQUEST)


class InvalidFiredDateException(StudentException):
    """Неверная дата увольнения"""
    def __init__(self, message="Дата увольнения может быть указана только для уровня 'Уволен'"):
        super().__init__(message, "INVALID_FIRED_DATE", status.HTTP_400_BAD_REQUEST)


class StudentAlreadyFiredException(StudentException):
    """Студент уже уволен"""
    def __init__(self, message="Студент уже находится в статусе 'Уволен'"):
        super().__init__(message, "STUDENT_ALREADY_FIRED", status.HTTP_400_BAD_REQUEST)


class InvalidCategoryException(StudentException):
    """Неверная категория студента"""
    def __init__(self, message="Неверная категория студента"):
        super().__init__(message, "INVALID_CATEGORY", status.HTTP_400_BAD_REQUEST)


class InvalidLevelException(StudentException):
    """Неверный уровень студента"""
    def __init__(self, message="Неверный уровень студента"):
        super().__init__(message, "INVALID_LEVEL", status.HTTP_400_BAD_REQUEST)


class IncompatibleCategoryBoardException(StudentException):
    """Студент несовместим с доской Канбан"""
    def __init__(self, message="Студент этой категории не может быть на данной доске"):
        super().__init__(message, "INCOMPATIBLE_CATEGORY_BOARD", status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ИСКЛЮЧЕНИЯ HR CALLS
# ============================================================================

class HrCallException(APIException):
    """Базовое исключение для операций с вызовами к HR"""
    pass


class HrCallNotFoundException(HrCallException):
    """Вызов к HR не найден"""
    def __init__(self, message="Вызов к HR не найден"):
        super().__init__(message, "HR_CALL_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class InvalidPersonTypeException(HrCallException):
    """Неверный тип лица для вызова"""
    def __init__(self, message="Неверный тип лица (должен быть 'student' или 'college')"):
        super().__init__(message, "INVALID_PERSON_TYPE", status.HTTP_400_BAD_REQUEST)


class MissingStudentException(HrCallException):
    """Студент не указан для вызова типа 'student'"""
    def __init__(self, message="Для типа 'student' необходимо указать студента"):
        super().__init__(message, "MISSING_STUDENT", status.HTTP_400_BAD_REQUEST)


class MissingFullNameException(HrCallException):
    """ФИО не указано для вызова типа 'college'"""
    def __init__(self, message="Для типа 'college' необходимо указать ФИО"):
        super().__init__(message, "MISSING_FULL_NAME", status.HTTP_400_BAD_REQUEST)


class InvalidYearException(HrCallException):
    """Год больше текущего"""
    def __init__(self, message="Год не может быть больше текущего года"):
        super().__init__(message, "INVALID_YEAR", status.HTTP_400_BAD_REQUEST)


class AutomaticHrCallException(HrCallException):
    """Попытка создать вызов для студента вручную (должен быть автоматическим)"""
    def __init__(self, message="Для студентов вызов создаётся автоматически при смене статуса"):
        super().__init__(message, "AUTOMATIC_HR_CALL", status.HTTP_400_BAD_REQUEST)


class InvalidVisitDatetimeException(HrCallException):
    """Неверная дата и время посещения"""
    def __init__(self, message="Дата и время посещения не может быть в будущем"):
        super().__init__(message, "INVALID_VISIT_DATETIME", status.HTTP_400_BAD_REQUEST)


class MissingReasonException(HrCallException):
    """Причина вызова не указана"""
    def __init__(self, message="Причина вызова обязательна"):
        super().__init__(message, "MISSING_REASON", status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ИСКЛЮЧЕНИЯ КАНБАН
# ============================================================================

class KanbanException(APIException):
    """Базовое исключение для операций с Канбан"""
    pass


class KanbanBoardNotFoundException(KanbanException):
    """Доска Канбан не найдена"""
    def __init__(self, message="Доска Канбан не найдена"):
        super().__init__(message, "KANBAN_BOARD_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class KanbanColumnNotFoundException(KanbanException):
    """Колонна Канбан не найдена"""
    def __init__(self, message="Колонна Канбан не найдена"):
        super().__init__(message, "KANBAN_COLUMN_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class StudentCardAlreadyExistsException(KanbanException):
    """Карта студента уже существует на доске"""
    def __init__(self, message="Студент уже находится на доске"):
        super().__init__(message, "STUDENT_CARD_ALREADY_EXISTS", status.HTTP_400_BAD_REQUEST)


class DuplicatePositionException(KanbanException):
    """Позиция на доске уже занята"""
    def __init__(self, message="Позиция уже занята на доске"):
        super().__init__(message, "DUPLICATE_POSITION", status.HTTP_400_BAD_REQUEST)


class InvalidColorException(KanbanException):
    """Неверный HEX цвет"""
    def __init__(self, message="Неверный HEX цвет"):
        super().__init__(message, "INVALID_COLOR", status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ИСКЛЮЧЕНИЯ АНАЛИТИКИ
# ============================================================================

class AnalyticsException(APIException):
    """Базовое исключение для операций с аналитикой"""
    pass


class AnalyticsSnapshotNotFoundException(AnalyticsException):
    """Снимок аналитики не найден"""
    def __init__(self, message="Снимок аналитики не найден"):
        super().__init__(message, "ANALYTICS_SNAPSHOT_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class InvalidDateRangeException(AnalyticsException):
    """Неверный диапазон дат"""
    def __init__(self, message="Дата начала не может быть больше даты конца"):
        super().__init__(message, "INVALID_DATE_RANGE", status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ИСКЛЮЧЕНИЯ ЭКСПОРТА
# ============================================================================

class ExportException(APIException):
    """Базовое исключение для операций с экспортом"""
    pass


class ExportTaskNotFoundException(ExportException):
    """Задача экспорта не найдена"""
    def __init__(self, message="Задача экспорта не найдена"):
        super().__init__(message, "EXPORT_TASK_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class ExportFailedException(ExportException):
    """Ошибка при экспорте"""
    def __init__(self, message="Ошибка при экспорте данных"):
        super().__init__(message, "EXPORT_FAILED", status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvalidExportFormatException(ExportException):
    """Неверный формат экспорта"""
    def __init__(self, message="Неверный формат экспорта (доступны: csv, excel, pdf)"):
        super().__init__(message, "INVALID_EXPORT_FORMAT", status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ИСКЛЮЧЕНИЯ ВАЛИДАЦИИ
# ============================================================================

class ValidationException(APIException):
    """Базовое исключение для валидации"""
    def __init__(self, message="Ошибка валидации", details=None):
        super().__init__(message, "VALIDATION_ERROR", status.HTTP_400_BAD_REQUEST)
        self.details = details or {}


class RequiredFieldException(ValidationException):
    """Обязательное поле не заполнено"""
    def __init__(self, field_name, message=None):
        msg = message or f"Поле '{field_name}' обязательно"
        super().__init__(msg, {"field": field_name})
        self.code = "REQUIRED_FIELD"


class InvalidFieldException(ValidationException):
    """Неверное значение поля"""
    def __init__(self, field_name, message=None):
        msg = message or f"Неверное значение для поля '{field_name}'"
        super().__init__(msg, {"field": field_name})
        self.code = "INVALID_FIELD"


class FieldTooLongException(ValidationException):
    """Значение поля слишком длинное"""
    def __init__(self, field_name, max_length, message=None):
        msg = message or f"Поле '{field_name}' не может быть длиннее {max_length} символов"
        super().__init__(msg, {"field": field_name, "max_length": max_length})
        self.code = "FIELD_TOO_LONG"


class FieldTooShortException(ValidationException):
    """Значение поля слишком короткое"""
    def __init__(self, field_name, min_length, message=None):
        msg = message or f"Поле '{field_name}' должно содержать не менее {min_length} символов"
        super().__init__(msg, {"field": field_name, "min_length": min_length})
        self.code = "FIELD_TOO_SHORT"


# ============================================================================
# ИСКЛЮЧЕНИЯ ОБЩИХ ОШИБОК
# ============================================================================

class ResourceNotFoundException(APIException):
    """Ресурс не найден"""
    def __init__(self, message="Запрашиваемый ресурс не найден"):
        super().__init__(message, "RESOURCE_NOT_FOUND", status.HTTP_404_NOT_FOUND)


class InvalidRequestException(APIException):
    """Неверный запрос"""
    def __init__(self, message="Неверный запрос"):
        super().__init__(message, "INVALID_REQUEST", status.HTTP_400_BAD_REQUEST)


class ConflictException(APIException):
    """Конфликт данных"""
    def __init__(self, message="Конфликт при обработке запроса"):
        super().__init__(message, "CONFLICT", status.HTTP_409_CONFLICT)


class InternalServerException(APIException):
    """Внутренняя ошибка сервера"""
    def __init__(self, message="Внутренняя ошибка сервера"):
        super().__init__(message, "INTERNAL_SERVER_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceUnavailableException(APIException):
    """Сервис недоступен"""
    def __init__(self, message="Сервис временно недоступен"):
        super().__init__(message, "SERVICE_UNAVAILABLE", status.HTTP_503_SERVICE_UNAVAILABLE)


class InvalidDataException(APIException):
    """Неверные данные"""
    def __init__(self, message="Неверные данные в запросе"):
        super().__init__(message, "INVALID_DATA", status.HTTP_400_BAD_REQUEST)

# ============================================================================
# ДРУГИЕ ИСКЛЮЧЕНИЯ
# ============================================================================

class DuplicateException(APIException):
    """Дублирующиеся данные"""
    def __init__(self, message="Такие данные уже существуют"):
        super().__init__(message, "DUPLICATE_ERROR", status.HTTP_400_BAD_REQUEST)


class InconsistentDataException(APIException):
    """Несогласованные данные"""
    def __init__(self, message="Несогласованные данные"):
        super().__init__(message, "INCONSISTENT_DATA", status.HTTP_400_BAD_REQUEST)
