# FRONTEND — Полная спецификация исключений и валидаторов

Файл содержит детальную информацию для frontend-разработчиков: полноценные описания всех API-исключений (code, HTTP-статус, триггеры, пример ответа, i18n-ключи и рекомендованные действия на фронтенде) и набор валидаторов с формальными правилами, регулярными выражениями и примерами.

## Стандарт формы ответа об ошибке

- Форма ответа (JSON):

```
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Неверный логин или пароль",
    "status": 401,
    "fields": { "username": "invalid", "password": "invalid" },
    "details": { "attempts_left": 2 }
  }
}
```

- Описание полей:
  - `code` (string): машиночитаемый идентификатор ошибки — используйте для i18n/логирования.
  - `message` (string): человекочитаемое сообщение (на бэке может быть i18n-ключ).
  - `status` (number): HTTP-статус.
  - `fields` (object, optional): карта `fieldName -> shortErrorCode` для inline-валидации.
  - `details` (object, optional): дополнительные данные (лимиты, список разрешённых значений и т.п.).

---

## Общие рекомендации по обработке ошибок на фронтенде

- При наличии `fields` — показывать inline ошибки у соответствующих input'ов.
- При отсутствии `fields` — показывать глобальный баннер/модал с `message`.
- Для 401/UNAUTHORIZED — очищать локальные токены и редиректить на страницу логина.
- Логировать `code` и `details` в аналитике (Sentry/GA).

---

## Exceptions (полный и конкретный список)

Формат каждой записи:

- `Name` — CODE — HTTP — Краткое описание
- Триггер: когда возникает
- Валидируемые входные данные: какие поля проверяются
- Пример ответа (JSON)
- i18n-ключ (рекомендуемый)
- Действия фронтенда (рекомендации)

### Аутентификация и авторизация

- `InvalidCredentialsException` — INVALID_CREDENTIALS — 401 — Неверные логин/пароль
  - Триггер: попытка входа с неверным `username` или `password`.
  - Вход: `{ username, password }`.
  - Пример ответа:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Неверный логин или пароль",
    "status": 401,
    "fields": { "username": "invalid", "password": "invalid" }
  }
}
```

- i18n: `auth.invalid_credentials`
- Фронтенд: показать общий баннер + подсветить оба поля; предлагать восстановление пароля после N попыток.

- `UnauthorizedException` — UNAUTHORIZED — 401 — Требуется аутентификация
  - Триггер: доступ к защищённому ресурсу без токена или с истёкшим/некорректным токеном.
  - Пример ответа: `{ "error": { "code":"UNAUTHORIZED","message":"Требуется авторизация","status":401 } }`
  - i18n: `auth.unauthorized`
  - Фронтенд: очистить лок.хранилище, редирект на логин, сохранить intended route.

- `AccessDeniedException` — ACCESS_DENIED — 403 — Доступ к ресурсу запрещён
  - Триггер: пользователь аутентифицирован, но не имеет доступа к ресурсу.
  - Пример: `{ "error": { "code":"ACCESS_DENIED","message":"Доступ запрещён","status":403 } }`
  - i18n: `auth.access_denied`
  - Фронтенд: показать сообщение и ссылку на поддержку/обратную связь.

- `PermissionDeniedException` — PERMISSION_DENIED — 403 — Недостаточно прав для действия
  - Триггер: попытка выполнить действие (удалить/редактировать), требующее ролей/прав.
  - Пример: `{ "error": { "code":"PERMISSION_DENIED","message":"Недостаточно прав","status":403 } }`
  - i18n: `auth.permission_denied`
  - Фронтенд: деактивировать/скрыть соответствующие UI-элементы; при попытке — показать объяснение.

### Пользователи (Users)

- `UserException` — USER_EXCEPTION — 400 — Базовая ошибка пользователей
  - Триггер: общая ошибка связанные с операциями над пользователем.
  - Рекомендация: отдавать более конкретные подклассы, если возможно.

- `UserNotFoundException` — USER_NOT_FOUND — 404 — Пользователь не найден
  - Триггер: поиск/запрос пользователя по id/email, которого нет.
  - Пример: `{ "error": { "code":"USER_NOT_FOUND","message":"Пользователь не найден","status":404,"details":{"user_id":123} } }`
  - i18n: `user.not_found`
  - Фронтенд: показать страницу 404 или подсказку, предложить создать пользователя.

- `UserAlreadyExistsException` — USER_ALREADY_EXISTS — 400 — Пользователь с такими данными уже существует
  - Триггер: регистрация/создание с существующим `email` или `username`.
  - Пример: `{ "error": { "code":"USER_ALREADY_EXISTS","message":"Пользователь уже существует","status":400,"fields":{"email":"duplicate"} } }`
  - i18n: `user.already_exists`
  - Фронтенд: подсветить `email`/`username`, предложить логин или восстановление пароля.

- `InvalidUsernameException` — INVALID_USERNAME — 400 — Неверный формат логина
  - Триггер: `username` не соответствует правилам (паттерн/длина).
  - Правила (рекомендация): латиница/числа/подчёркивания, 3–30 символов. Регекс: `^[A-Za-z0-9_]{3,30}$`.
  - Пример fields: `{ "username":"invalid_format" }`
  - i18n: `user.invalid_username`
  - Фронтенд: показать требования к имени пользователя при вводе.

- `InvalidPasswordException` — INVALID_PASSWORD — 400 — Пароль не соответствует требованиям
  - Триггер: пароль не проходит по политике (например, min 8, символы/числа).
  - Пример fields: `{ "password":"too_weak" }`
  - Рекомендации пароля: минимум 8 символов, буквы и цифры; при необходимости спецсимволы и верхний регистр.
  - i18n: `user.invalid_password`

- `PasswordMismatchException` — PASSWORD_MISMATCH — 400 — Пароли не совпадают
  - Триггер: `password` !== `confirm_password`.
  - Пример fields: `{ "confirm_password":"mismatch" }`
  - i18n: `user.password_mismatch`

- `InvalidEmailException` — INVALID_EMAIL — 400 — Неверный формат email
  - Триггер: email не проходит базовую валидацию.
  - Регекс: `^[^\s@]+@[^\s@]+\.[^\s@]+$`.
  - Пример: `{ "error": { "code":"INVALID_EMAIL","message":"Неверный формат email","status":400,"fields":{"email":"invalid_format"} } }`
  - i18n: `user.invalid_email`

- `InvalidTelegramException` — INVALID_TELEGRAM — 400 — Неверный формат Telegram username
  - Триггер: `telegram` содержит пробелы или недопустимые символы.
  - Правила: возможно с `@`, 5–32 символа, `[A-Za-z0-9_]{5,32}`.
  - i18n: `user.invalid_telegram`

- `MissingContactInfoException` — MISSING_CONTACT_INFO — 400 — Не указаны контактные данные
  - Триггер: при требовании хотя бы одного контакта (email/telegram/phone) все пусты.
  - Пример fields: `{ "email":"required","telegram":"required","phone":"required" }`
  - i18n: `user.missing_contact`

### Студенты (Students)

- `StudentException` — STUDENT_EXCEPTION — 400 — Базовая ошибка студентов

- `StudentNotFoundException` — STUDENT_NOT_FOUND — 404 — Студент не найден
  - Триггер: lookup по `student_id`.
  - Пример details: `{ "student_id": 42 }`.
  - i18n: `student.not_found`

- `InvalidAgeException` — INVALID_AGE — 400 — Возраст вне допустимого диапазона
  - Триггер: возраст (либо рассчитанный по `birth_date`, либо указан явно) не входит в [14, 30].
  - Пример: `{ "error": { "code":"INVALID_AGE","message":"Возраст должен быть в диапазоне 14–30","status":400,"details":{"min":14,"max":30} } }`
  - i18n: `student.invalid_age`

- `AgeExceedsLimitException` — AGE_EXCEEDS_LIMIT — 400 — Возраст больше допустимого лимита
  - Триггер: возраст > max (например >30).

- `InvalidPhoneException` — INVALID_PHONE — 400 — Неверный формат телефона
  - Триггер: телефон не проходит `validate_phone_number`.
  - Рекомендуется поддерживать E.164: `^\+?\d{10,15}$`.
  - i18n: `student.invalid_phone`

- `PhoneInvalidFormatException` — PHONE_INVALID_FORMAT — 400 — Телефон содержит недопустимые символы
  - Триггер: буквы/символы после очистки.

- `PhoneTooLongException` — PHONE_TOO_LONG — 400 — Телефон слишком длинный
  - Триггер: более 15 цифр (по E.164), details: `{ "max_digits": 15 }`.

- `InvalidNameException` — INVALID_NAME — 400 — Неправильный формат имени/фамилии/отчества
  - Триггер: цифры или запрещённые символы в имени, превышение длины.
  - Регекс (пример): `^[A-Za-zА-Яа-яЁё'\-\s]{1,64}$`.
  - i18n: `student.invalid_name`

- `InvalidBirthDateException` — INVALID_BIRTH_DATE — 400 — Дата рождения некорректна (будущая/слишком молод)
  - Триггер: `birth_date` > today или возраст < 14.
  - details: `{ "min_age": 14 }`.

- `InvalidFiredDateException` — INVALID_FIRED_DATE — 400 — Дата увольнения указана некорректно
  - Триггер: `fired_date` < `hired_date` или `fired_date` > today.

- `StudentAlreadyFiredException` — STUDENT_ALREADY_FIRED — 400 — Студент уже уволен
  - Триггер: повторная попытка пометить уволенным уже уволенного студента.

- `InvalidCategoryException` — INVALID_CATEGORY — 400 — Неверная категория студента
  - Триггер: `category` не в списке допустимых; details: `{ "allowed": ["fulltime","parttime"] }`.

- `InvalidLevelException` — INVALID_LEVEL — 400 — Неверный уровень студента

- `IncompatibleCategoryBoardException` — INCOMPATIBLE_CATEGORY_BOARD — 400 — Несовместимость категории с доской
  - Триггер: перенос карточки на доску, где категория не поддерживается.
  - details: `{ "board_id": 10, "allowed_categories": ["intern","junior"] }`.

### HR Calls

- `HrCallException` — HR_CALL_EXCEPTION — 400

- `HrCallNotFoundException` — HR_CALL_NOT_FOUND — 404

- `InvalidPersonTypeException` — INVALID_PERSON_TYPE — 400 — Неверный тип лица для вызова
  - Триггер: `person_type` не в `['student','college','other']`.
  - fields: `{ "person_type": "invalid_choice" }`.

- `MissingStudentException` — MISSING_STUDENT — 400 — Для типа 'student' не указан студент
  - Триггер: `person_type == 'student'` и нет `student_id`.

- `MissingFullNameException` — MISSING_FULL_NAME — 400 — Для типа 'college' не указано ФИО

- `InvalidYearException` — INVALID_YEAR — 400 — Год указан неверно (больше текущего)
  - fields: `{ "year": "future" }`.

- `AutomaticHrCallException` — AUTOMATIC_HR_CALL — 400 — Попытка создать автоматический вызов вручную

- `InvalidVisitDatetimeException` — INVALID_VISIT_DATETIME — 400 — Дата/время посещения некорректно
  - Триггер: формат, пересечение по расписанию или дата в прошлом (если запрещено).

- `MissingReasonException` — MISSING_REASON — 400 — Причина вызова не указана
  - fields: `{ "reason": "required" }`.

### Канбан (Kanban)

- `KanbanException` — KANBAN_EXCEPTION — 400

- `KanbanBoardNotFoundException` — KANBAN_BOARD_NOT_FOUND — 404

- `KanbanColumnNotFoundException` — KANBAN_COLUMN_NOT_FOUND — 404

- `StudentCardAlreadyExistsException` — STUDENT_CARD_ALREADY_EXISTS — 400 — Карта студента уже существует
  - fields: `{ "student_id": "duplicate" }`.

- `DuplicatePositionException` — DUPLICATE_POSITION — 400 — Позиция на доске занята
  - details: `{ "position": 3, "column_id": 5 }`.

- `InvalidColorException` — INVALID_COLOR — 400 — Неверный HEX-цвет
  - Регекс: `^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$`.
  - fields: `{ "color": "invalid_format" }`.

### Аналитика (Analytics)

- `AnalyticsException` — ANALYTICS_EXCEPTION — 400

- `AnalyticsSnapshotNotFoundException` — ANALYTICS_SNAPSHOT_NOT_FOUND — 404

- `InvalidDateRangeException` — INVALID_DATE_RANGE — 400 — Неверный диапазон дат
  - Триггер: `start > end` или период превышает допустимый (например, > 365 дней).
  - details: `{ "max_range_days": 365 }`.

### Экспорт (Export)

- `ExportException` — EXPORT_EXCEPTION — 400

- `ExportTaskNotFoundException` — EXPORT_TASK_NOT_FOUND — 404

- `ExportFailedException` — EXPORT_FAILED — 500 — Ошибка при экспорте данных
  - details: `{ "reason": "timeout" }`.

- `InvalidExportFormatException` — INVALID_EXPORT_FORMAT — 400 — Неверный формат экспорта (ожидался csv/xlsx/json)
  - details: `{ "allowed": ["csv","xlsx","json"] }`.

### Валидация (Validation)

- `ValidationException` — VALIDATION_ERROR — 400 — Общая ошибка валидации
  - Формат: `fields` содержит `fieldName -> shortErrorCode`.

- `RequiredFieldException` — REQUIRED_FIELD — 400
  - fields: `{ "field": "required" }`.

- `InvalidFieldException` — INVALID_FIELD — 400

- `FieldTooLongException` — FIELD_TOO_LONG — 400
  - details: `{ "max_length": 255 }`.

- `FieldTooShortException` — FIELD_TOO_SHORT — 400
  - details: `{ "min_length": 2 }`.

### Общие/Прочие

- `ResourceNotFoundException` — RESOURCE_NOT_FOUND — 404

- `InvalidRequestException` — INVALID_REQUEST — 400

- `ConflictException` — CONFLICT — 409 — Конфликт при обработке запроса
  - Триггер: попытка удалить/изменить ресурс, имеющий зависимости.

- `InternalServerException` — INTERNAL_SERVER_ERROR — 500
  - Фронтенд: общий баннер "Сервис временно недоступен"; возможность ретрая через некоторое время.

- `ServiceUnavailableException` — SERVICE_UNAVAILABLE — 503

- `InvalidDataException` — INVALID_DATA — 400

- `DuplicateException` — DUPLICATE_ERROR — 400

- `InconsistentDataException` — INCONSISTENT_DATA — 400 — Несогласованные данные
  - Триггер: конфликтующие поля (например, `type='student'` и отсутствует `student_id`).

### Файлы (File errors)

- `FileException` — FILE_EXCEPTION — 400

- `FileTooLargeException` — FILE_TOO_LARGE — 413 — Файл слишком большой
  - details: `{ "max_size_bytes": 10485760 }` (пример 10MB).
  - Фронтенд: блокировать загрузку, показывать лимит, предлагать сжатие.

- `InvalidFileTypeException` — INVALID_FILE_TYPE — 400 — Неверный тип файла
  - details: `{ "allowed": ["image/png","image/jpeg","application/pdf"] }`.

- `FileUploadFailedException` — FILE_UPLOAD_FAILED — 400 — Ошибка при загрузке файла
  - details: `{ "retryable": true }`.

---

## Validators (полные определения)

Формат: `name` — подпись — параметры — правила — regex (если есть) — возвращаемые коды ошибок — примеры.

### 1) Телефоны

- `validate_phone_number(phone: string, options?: {allowE164?: boolean}) -> { valid: boolean, error?: string, normalized?: string }`
  - Правила: удаляем пробелы, скобки, дефисы; допускаем `+` в начале; затем должны остаться 10–15 цифр.
  - Регекс: `^\+?\d{10,15}$`.
  - Ошибки: `INVALID_PHONE`, `PHONE_TOO_LONG`, `PHONE_INVALID_FORMAT`.
  - Примеры: валид: `+79161234567` -> normalized `+79161234567`; невалид: `+7(916)123-45-67x` -> `PHONE_INVALID_FORMAT`.
  - UI: маска ввода и подсказка "Формат: +7XXXXXXXXXX".

- `validate_phone_digits_only(phone: string) -> { valid, error }`
  - Правило: после удаления пробелов/знаков — только цифры.
  - Регекс: `^\d+$`.
  - Ошибка: `PHONE_INVALID_FORMAT`.

### 2) Возраст и даты

- `calculate_age(birth_date: string|Date) -> number`
  - Описание: возвращает целые годы (полная логика сравнения год/месяц/день).

- `validate_birth_date(birth_date: string|Date, min_age=14, max_age=30) -> {valid,error,age}`
  - Правила: дата в ISO, не в будущем, возраст в диапазоне `[min_age,max_age]`.
  - Ошибки: `INVALID_BIRTH_DATE`, `INVALID_AGE`.
  - Пример невалидного: `2050-01-01` -> `INVALID_BIRTH_DATE`.

- `validate_age(age: number, min=14, max=30) -> {valid,error}`
  - Правила: integer, `min <= age <= max`.
  - Ошибки: `INVALID_AGE`, `AGE_EXCEEDS_LIMIT`.

- `validate_year(year: number) -> {valid,error}`
  - Правило: `year <= currentYear`.
  - Ошибка: `INVALID_YEAR`.

### 3) Имена

- `validate_name(name: string, min=1, max=64) -> {valid,error}`
  - Правила: только буквы (лат/кирил), пробел, дефис, апостроф; длина в пределах.
  - Регекс: `^[A-Za-zА-Яа-яЁё'\-\s]{1,64}$`.
  - Ошибки: `INVALID_NAME`, `FIELD_TOO_LONG`, `FIELD_TOO_SHORT`.

- `validate_first_name`, `validate_last_name`, `validate_patronymic` — специализированные вызовы `validate_name` с возможными другими лимитами.

### 4) Текстовые поля

- `validate_text_field(text: string, {min_len=0,max_len=1000,strip_html=true}) -> {valid,error}`
  - Правила: проверка длины; опционально удаление HTML-тегов; запрет control-символов.
  - Ошибки: `FIELD_TOO_SHORT`, `FIELD_TOO_LONG`, `INVALID_FIELD`.

- `validate_reason_field(text)` — дополнительно: запрет пустых строк, минимальная семантическая длина (напр., 10 символов).

### 5) Datetime

- `validate_datetime_not_future(dt: string|Date) -> {valid,error}`
  - Правило: `dt <= now`.
  - Ошибки: `INVALID_VISIT_DATETIME`, `INVALID_DATETIME`.

- `validate_datetime_in_range(dt, {min, max}) -> {valid,error}`
  - Правило: `min <= dt <= max`.
  - Ошибка: `INVALID_DATE_RANGE`.

### 6) Enum/Choices

- `validate_choice(value, allowed: any[]) -> {valid,error,details?:{allowed}}`
  - Ошибка: `INVALID_CHOICE`.

### 7) Числовые поля

- `validate_positive_integer(value) -> {valid,error}`
  - Правило: integer >= 0
  - Ошибки: `INVALID_FIELD`.

- `validate_decimal_range(value, min, max, precision?) -> {valid,error}`
  - Правило: numeric и `min <= value <= max`, опционально проверка `precision`.
  - Ошибки: `OUT_OF_RANGE`, `INVALID_FIELD`.

### 8) Файлы

- `validate_file_size(size_bytes, max_size_bytes) -> {valid,error}`
  - Ошибка: `FILE_TOO_LARGE`.
  - UI: показывать человекочитаемый лимит (`10 MB`).

- `validate_file_extension(filename, allowed_extensions) -> {valid,error}`
  - Правило: сравнение расширения в нижнем регистре.
  - Ошибка: `INVALID_FILE_TYPE`.

### 9) Комбинированные

- `validate_student_data(studentObj) -> { valid: boolean, fields: { [fieldName]: errorCode }, details?: {} }`
  - Описание: запускает все релевантные валидаторы и агрегирует `fields`.
  - Пример возврата при ошибках:

```json
{
  "valid": false,
  "fields": {
    "first_name": "INVALID_NAME",
    "birth_date": "INVALID_BIRTH_DATE",
    "phone": "INVALID_PHONE"
  }
}
```

---

## i18n-ключи (рекомендуемые)

- auth.invalid_credentials = "Неверный логин или пароль"
- auth.unauthorized = "Требуется авторизация"
- auth.access_denied = "Доступ запрещён"
- user.invalid_email = "Неверный формат email"
- user.invalid_password = "Пароль не соответствует требованиям"
- student.invalid_age = "Возраст должен быть между 14 и 30 годами"
- file.too_large = "Файл слишком большой (максимум {max})"
- validation.required = "Поле обязательно для заполнения"

(переходите к JSON-экспорту i18n по запросу)

---

## Примеры интеграции на фронтенде (быстро)

- Обработчик ответа об ошибке:

```js
function handleApiError(resp) {
  const err = resp.error;
  if (!err) return;
  switch (err.code) {
    case "INVALID_CREDENTIALS":
      showToast(t("auth.invalid_credentials"));
      break;
    case "UNAUTHORIZED":
      logoutAndRedirect();
      break;
    default:
      showBanner(err.message || t(`error.${err.code}`));
  }
  if (err.fields) applyFieldErrors(err.fields);
}
```

---

## Дальше

- Могу заменить существующий `FRONTEND_API_ERRORS_VALIDATORS.md` этим файлом, сгенерировать `error.schema.json` или экспорт i18n-ключей. Скажите, что сделать дальше.
