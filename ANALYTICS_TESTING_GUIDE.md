# Руководство по тестированию аналитики

## 1. Запуск сервера

```bash
cd /Users/samir/Desktop/Backend_Pytomnic/Backend-Pytomnik
python manage.py runserver
```

## 2. Тестирование страницы аналитики в админке

### Доступ к странице аналитики:
1. Откройте браузер и перейдите: `http://localhost:8000/pytomnic-adminka-cats/`
2. Войдите в админку с вашими учетными данными
3. Найдите раздел "Analytics" в списке приложений
4. Кликните на "Analytics" - откроется дашборд аналитики

**Прямая ссылка:** `http://localhost:8000/pytomnic-adminka-cats/analytics/analytics/`

### Что проверить на странице:
- ✅ Отображаются метрики: всего студентов, активные, уволенные
- ✅ HR-вызовы за последние 30 дней
- ✅ Новые студенты за 30 дней
- ✅ Изменения уровней за 30 дней
- ✅ Распределение по уровням (green, yellow, red, black)
- ✅ Распределение по статусам (active, fired)
- ✅ Распределение по категориям (колледжисты, патриоты и т.д.)

---

## 3. Тестирование скачивания полной аналитики

### Через админку:
1. На странице аналитики найдите кнопку **"Скачать полную аналитику"**
2. Кликните на кнопку
3. Должен скачаться Excel-файл с именем типа: `Analytics_cats_20260326_075942.xlsx`

### Через прямую ссылку:
```bash
# В браузере или через curl
curl -o full_analytics.xlsx "http://localhost:8000/analytics/download/?type=full" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

### Что проверить в Excel-файле:
- ✅ Лист "Аналитика" с тремя таблицами:
  - Распределение по уровням (с процентами)
  - Распределение по статусам (с процентами)
  - Распределение по категориям (с процентами)
- ✅ Лист "Диаграммы" с тремя круговыми диаграммами
- ✅ Корректные данные и форматирование

---

## 4. Тестирование скачивания аналитики за месяц

### Через админку:
1. На странице аналитики найдите форму **"Скачать месячную аналитику"**
2. Выберите месяц в селекторе (например, "2026-02" для февраля 2026)
3. Кликните кнопку **"Скачать месячную аналитику"**
4. Должен скачаться Excel-файл с именем типа: `Analytics_20260201_20260228_075942.xlsx`

### Через прямую ссылку:
```bash
# Скачать аналитику за февраль 2026
curl -o month_analytics.xlsx "http://localhost:8000/analytics/download/?type=month&month=2026-02" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"

# Скачать аналитику за март 2026
curl -o month_analytics.xlsx "http://localhost:8000/analytics/download/?type=month&month=2026-03" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

### Что проверить в Excel-файле:
- ✅ Лист "Аналитика" с таблицей метрик за период:
  - Уволенные коты (с учетом точности даты)
  - Вызовы к HR (все вызовы за период)
  - Новые коты (созданные в период)
  - Смены уровней (все изменения за период)
- ✅ Корректное название периода в заголовке
- ✅ Правильные данные за выбранный месяц

---

## 5. Тестирование API эндпоинтов

### 5.1. Dashboard API (общая аналитика)
```bash
# Получить общую аналитику
curl -X GET "http://localhost:8000/api/v1/dashboard/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# С периодом
curl -X GET "http://localhost:8000/api/v1/dashboard/?date_from=2026-02-01&date_to=2026-02-28" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Ожидаемый ответ:**
```json
{
  "success": true,
  "total_students": 150,
  "active_students": 120,
  "fired_students": 30,
  "called_hr_students": 15,
  "new_students_total": 10,
  "level_changes_total": 25,
  "period": {
    "date_from": "2026-02-01",
    "date_to": "2026-02-28",
    "new_students_total": 5,
    "level_changes_total": 12,
    "fired_students_total": 3,
    "called_hr_students_total": 8
  },
  "students_by_level": [...],
  "students_by_status": [...],
  "students_by_category": [...],
  "updated_at": "2026-03-26T07:59:42.123456Z"
}
```

### 5.2. Level Distribution API
```bash
curl -X GET "http://localhost:8000/api/v1/levels/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Ожидаемый ответ:**
```json
{
  "success": true,
  "levels": [
    {
      "level": "green",
      "display_name": "Green",
      "count": 50,
      "percentage": 41.7
    },
    {
      "level": "yellow",
      "display_name": "Yellow",
      "count": 40,
      "percentage": 33.3
    }
  ],
  "total_active": 120
}
```

---

## 6. Тестирование логики подсчета уволенных

### Создание тестовых данных:

```python
# В Django shell: python manage.py shell
from apps.students.models import Student
from datetime import date

# Студент уволенный 15 февраля (точная дата)
student1 = Student.objects.create(
    first_name="Иван",
    last_name="Иванов",
    category="college",
    level="fired",
    status="fired",
    fired_date=date(2026, 2, 15)  # день != 1, точная дата
)

# Студент уволенный в феврале (месячная точность)
student2 = Student.objects.create(
    first_name="Петр",
    last_name="Петров",
    category="college",
    level="fired",
    status="fired",
    fired_date=date(2026, 2, 1)  # день = 1, месячная точность
)

# Студент уволенный в марте
student3 = Student.objects.create(
    first_name="Сидор",
    last_name="Сидоров",
    category="college",
    level="fired",
    status="fired",
    fired_date=date(2026, 3, 10)
)
```

### Проверка подсчета:

```bash
# Скачать аналитику за февраль 2026
curl -o feb_analytics.xlsx "http://localhost:8000/analytics/download/?type=month&month=2026-02" \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Ожидаемый результат в Excel:**
- Уволенные коты: **2** (student1 с точной датой 15.02 + student2 с месячной точностью февраль)
- student3 НЕ должен учитываться (март)

---

## 7. Тестирование через Python скрипт

Создайте файл `test_analytics.py`:

```python
import requests
from datetime import date

# Настройки
BASE_URL = "http://localhost:8000"
# Получите токен через /api/v1/login/
JWT_TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json"
}

def test_dashboard():
    """Тест общей аналитики"""
    response = requests.get(f"{BASE_URL}/api/v1/dashboard/", headers=headers)
    print("Dashboard API:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print(f"  Всего студентов: {data['total_students']}")
        print(f"  Активных: {data['active_students']}")
        print(f"  Уволенных: {data['fired_students']}")
    print()

def test_dashboard_with_period():
    """Тест аналитики за период"""
    params = {
        "date_from": "2026-02-01",
        "date_to": "2026-02-28"
    }
    response = requests.get(f"{BASE_URL}/api/v1/dashboard/", headers=headers, params=params)
    print("Dashboard API с периодом:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        if data.get('period'):
            print(f"  Новых студентов: {data['period']['new_students_total']}")
            print(f"  Уволенных: {data['period']['fired_students_total']}")
            print(f"  Вызовов к HR: {data['period']['called_hr_students_total']}")
    print()

def test_levels():
    """Тест распределения по уровням"""
    response = requests.get(f"{BASE_URL}/api/v1/levels/", headers=headers)
    print("Levels API:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        print(f"  Всего активных: {data['total_active']}")
        for level in data['levels']:
            print(f"  {level['display_name']}: {level['count']} ({level['percentage']}%)")
    print()

def test_download_full():
    """Тест скачивания полной аналитики"""
    # Используйте session cookie вместо JWT для download
    response = requests.get(f"{BASE_URL}/analytics/download/?type=full")
    print("Download Full Analytics:", response.status_code)
    if response.status_code == 200:
        with open("test_full_analytics.xlsx", "wb") as f:
            f.write(response.content)
        print("  Файл сохранен: test_full_analytics.xlsx")
    print()

def test_download_month():
    """Тест скачивания месячной аналитики"""
    params = {
        "type": "month",
        "month": "2026-02"
    }
    response = requests.get(f"{BASE_URL}/analytics/download/", params=params)
    print("Download Month Analytics:", response.status_code)
    if response.status_code == 200:
        with open("test_month_analytics.xlsx", "wb") as f:
            f.write(response.content)
        print("  Файл сохранен: test_month_analytics.xlsx")
    print()

if __name__ == "__main__":
    print("=== Тестирование аналитики ===\n")
    test_dashboard()
    test_dashboard_with_period()
    test_levels()
    # test_download_full()  # Требует session cookie
    # test_download_month()  # Требует session cookie
```

Запуск:
```bash
python test_analytics.py
```

---

## 8. Проверка прав доступа

### Тест 1: Доступ для HR/TEV/Admin
```python
# Пользователь с ролью 'hr', 'tev' или 'admin' должен иметь доступ
# Проверьте, что API возвращает 200 OK
```

### Тест 2: Доступ для других ролей
```python
# Пользователь с ролью 'user' НЕ должен иметь доступ
# Проверьте, что API возвращает 403 Forbidden
```

---

## 9. Чек-лист тестирования

- [ ] Страница аналитики открывается в админке
- [ ] Все метрики отображаются корректно
- [ ] Распределения показывают правильные данные
- [ ] Кнопка "Скачать полную аналитику" работает
- [ ] Форма "Скачать месячную аналитику" работает
- [ ] Excel-файлы открываются без ошибок
- [ ] Данные в Excel соответствуют данным на странице
- [ ] API эндпоинты возвращают корректные JSON
- [ ] Аналитика за период считается правильно
- [ ] Уволенные студенты учитываются с правильной точностью
- [ ] Права доступа работают корректно
- [ ] Дизайн выглядит профессионально и ненавязчиво

---

## 10. Возможные проблемы и решения

### Проблема: 403 Forbidden при доступе к аналитике
**Решение:** Убедитесь, что у пользователя есть права:
```python
# В Django shell
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='your_username')
user.role = 'hr'  # или 'tev', 'admin'
user.save()
```

### Проблема: Пустые данные в аналитике
**Решение:** Создайте тестовых студентов:
```python
from apps.students.models import Student
Student.objects.create(
    first_name="Тест",
    last_name="Тестов",
    category="college",
    level="green",
    status="active"
)
```

### Проблема: Ошибка при скачивании Excel
**Решение:** Проверьте, что установлен openpyxl:
```bash
pip install openpyxl
```

---

## Готово! 🎉

Теперь у вас есть полное руководство по тестированию всего функционала аналитики.
