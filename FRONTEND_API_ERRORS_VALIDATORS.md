# FRONTEND — Список исключений и валидаторов (имена и короткие описания)

Формат: имя_исключения — CODE — HTTP_STATUS — Краткое описание назначения

## Исключения (Exceptions)

Базовый класс:

- APIException — APIException — 400 — Общий базовый класс для всех API-ошибок

Аутентификация и авторизация:

- InvalidCredentialsException — INVALID_CREDENTIALS — 401 — Неверные логин/пароль
- UnauthorizedException — UNAUTHORIZED — 401 — Требуется аутентификация
- AccessDeniedException — ACCESS_DENIED — 403 — Доступ к ресурсу запрещён
- PermissionDeniedException — PERMISSION_DENIED — 403 — Недостаточно прав для действия

Пользователи (Users):

- UserException — USER_EXCEPTION — 400 — Базовая ошибка пользователей
- UserNotFoundException — USER_NOT_FOUND — 404 — Пользователь не найден
- UserAlreadyExistsException — USER_ALREADY_EXISTS — 400 — Пользователь с такими данными уже существует
- InvalidUsernameException — INVALID_USERNAME — 400 — Неверный формат логина
- InvalidPasswordException — INVALID_PASSWORD — 400 — Пароль не соответствует требованиям
- PasswordMismatchException — PASSWORD_MISMATCH — 400 — Пароли не совпадают
- InvalidEmailException — INVALID_EMAIL — 400 — Неверный формат email
- InvalidTelegramException — INVALID_TELEGRAM — 400 — Неверный формат Telegram username
- MissingContactInfoException — MISSING_CONTACT_INFO — 400 — Не указаны контактные данные (email/telegram)

Студенты (Students):

- StudentException — STUDENT_EXCEPTION — 400 — Базовая ошибка студентов
- StudentNotFoundException — STUDENT_NOT_FOUND — 404 — Студент не найден
- InvalidAgeException — INVALID_AGE — 400 — Возраст вне допустимого диапазона
- AgeExceedsLimitException — AGE_EXCEEDS_LIMIT — 400 — Возраст больше допустимого лимита
- InvalidPhoneException — INVALID_PHONE — 400 — Неверный формат телефона
- PhoneInvalidFormatException — PHONE_INVALID_FORMAT — 400 — Телефон содержит недопустимые символы
- PhoneTooLongException — PHONE_TOO_LONG — 400 — Телефон слишком длинный
- InvalidNameException — INVALID_NAME — 400 — Неправильный формат имени/фамилии/отчества
- InvalidBirthDateException — INVALID_BIRTH_DATE — 400 — Дата рождения некорректна (будущая)
- InvalidFiredDateException — INVALID_FIRED_DATE — 400 — Дата увольнения указана некорректно
- StudentAlreadyFiredException — STUDENT_ALREADY_FIRED — 400 — Студент уже уволен
- InvalidCategoryException — INVALID_CATEGORY — 400 — Неверная категория студента
- InvalidLevelException — INVALID_LEVEL — 400 — Неверный уровень студента
- IncompatibleCategoryBoardException — INCOMPATIBLE_CATEGORY_BOARD — 400 — Несовместимость категории с доской

HR Calls:

- HrCallException — HR_CALL_EXCEPTION — 400 — Базовая ошибка для вызовов к HR
- HrCallNotFoundException — HR_CALL_NOT_FOUND — 404 — Вызов к HR не найден
- InvalidPersonTypeException — INVALID_PERSON_TYPE — 400 — Неверный тип лица для вызова
- MissingStudentException — MISSING_STUDENT — 400 — Для типа 'student' не указан студент
- MissingFullNameException — MISSING_FULL_NAME — 400 — Для типа 'college' не указано ФИО
- InvalidYearException — INVALID_YEAR — 400 — Год указан неверно (больше текущего)
- AutomaticHrCallException — AUTOMATIC_HR_CALL — 400 — Попытка создать автоматический вызов вручную
- InvalidVisitDatetimeException — INVALID_VISIT_DATETIME — 400 — Дата/время посещения некорректно
- MissingReasonException — MISSING_REASON — 400 — Причина вызова не указана

Канбан (Kanban):

- KanbanException — KANBAN_EXCEPTION — 400 — Базовая ошибка Канбан
- KanbanBoardNotFoundException — KANBAN_BOARD_NOT_FOUND — 404 — Доска Канбан не найдена
- KanbanColumnNotFoundException — KANBAN_COLUMN_NOT_FOUND — 404 — Колонка Канбан не найдена
- StudentCardAlreadyExistsException — STUDENT_CARD_ALREADY_EXISTS — 400 — Карта студента уже существует
- DuplicatePositionException — DUPLICATE_POSITION — 400 — Позиция на доске занята
- InvalidColorException — INVALID_COLOR — 400 — Неверный HEX-цвет

Аналитика (Analytics):

- AnalyticsException — ANALYTICS_EXCEPTION — 400 — Базовая ошибка аналитики
- AnalyticsSnapshotNotFoundException — ANALYTICS_SNAPSHOT_NOT_FOUND — 404 — Снимок аналитики не найден
- InvalidDateRangeException — INVALID_DATE_RANGE — 400 — Неверный диапазон дат

Экспорт (Export):

- ExportException — EXPORT_EXCEPTION — 400 — Базовая ошибка экспорта
- ExportTaskNotFoundException — EXPORT_TASK_NOT_FOUND — 404 — Задача экспорта не найдена
- ExportFailedException — EXPORT_FAILED — 500 — Ошибка при экспорте данных
- InvalidExportFormatException — INVALID_EXPORT_FORMAT — 400 — Неверный формат экспорта

Валидация (Validation):

- ValidationException — VALIDATION_ERROR — 400 — Общая ошибка валидации
- RequiredFieldException — REQUIRED_FIELD — 400 — Обязательное поле не заполнено
- InvalidFieldException — INVALID_FIELD — 400 — Неверное значение поля
- FieldTooLongException — FIELD_TOO_LONG — 400 — Значение поля слишком длинное
- FieldTooShortException — FIELD_TOO_SHORT — 400 — Значение поля слишком короткое

Общие/Прочие:

- ResourceNotFoundException — RESOURCE_NOT_FOUND — 404 — Запрашиваемый ресурс не найден
- InvalidRequestException — INVALID_REQUEST — 400 — Неверный запрос
- ConflictException — CONFLICT — 409 — Конфликт при обработке запроса
- InternalServerException — INTERNAL_SERVER_ERROR — 500 — Внутренняя ошибка сервера
- ServiceUnavailableException — SERVICE_UNAVAILABLE — 503 — Сервис недоступен
- InvalidDataException — INVALID_DATA — 400 — Неверные данные в запросе
- DuplicateException — DUPLICATE_ERROR — 400 — Дублирование данных
- InconsistentDataException — INCONSISTENT_DATA — 400 — Несогласованные данные

Файлы (File errors):

- FileException — FILE_EXCEPTION — 400 — Базовая ошибка файловых операций
- FileTooLargeException — FILE_TOO_LARGE — 413 — Файл слишком большой
- InvalidFileTypeException — INVALID_FILE_TYPE — 400 — Неверный тип файла
- FileUploadFailedException — FILE_UPLOAD_FAILED — 400 — Ошибка при загрузке файла

## Валидаторы (Validators)

Телефоны:

- validate_phone_number — Валидирует формат и длину телефонного номера
- validate_phone_digits_only — Проверяет, что телефон состоит только из цифр

Возраст и даты:

- validate_birth_date — Проверяет дату рождения и возраст (14–30)
- calculate_age — Возвращает возраст по дате рождения
- validate_age — Проверяет числовой возраст (14–30)
- validate_year — Проверяет, что год не больше текущего
- validate_future_year — Проверяет корректность года относительно текущего

Имена:

- validate_name — Общая валидация имени (символы и длина)
- validate_first_name — Валидация имени
- validate_last_name — Валидация фамилии
- validate_patronymic — Валидация отчества

Текстовые поля:

- validate_text_field — Общая валидация текста (min/max длина)
- validate_reason_field — Валидация поля "причина"
- validate_solution_field — Валидация поля "решение"

Datetime:

- validate_datetime_not_future — Проверяет, что дата/время не в будущем
- validate_datetime_in_range — Проверяет, что дата в заданном диапазоне

Enum/Choices:

- validate_choice — Проверяет значение на вхождение в список опций

Числовые поля:

- validate_positive_integer — Проверяет положительное целое число
- validate_decimal_range — Проверяет число в диапазоне

Файлы:

- validate_file_size — Проверяет размер файла
- validate_file_extension — Проверяет расширение файла

Комбинированные:

- validate_student_data — Комплексная валидация данных студента
