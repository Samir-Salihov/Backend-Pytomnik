<div align="center">

# 🐱 Pytomnic Backend

**Backend система управления питомником для колледжа**

[![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16.1-ff3333?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![WebSocket](https://img.shields.io/badge/WebSocket-Channels-FF9900?style=for-the-badge&logo=socket.io&logoColor=white)](https://channels.readthedocs.io/)

---

### 🌍 Language / Язык

<details>
<summary>🇬🇧 English</summary>
<br>

## 📋 About Project
Backend part of the student management system for college. Full-featured administrative panel with analytics, export, Kanban board and real-time updates.

## ✨ Features
| Module | Description |
|--------|-------------|
| 🎓 **Students** | Full profile management, level tracking, statuses, categories, history of changes |
| 📋 **HR Calls** | HR department call system with classification, attachment files and export |
| 📊 **Analytics** | Interactive dashboard with period selection, charts and dynamic counters |
| 📤 **Export** | Generation of Excel/CSV reports with customizable fields |
| 📋 **Kanban** | Real-time Kanban board with drag&drop via WebSockets |
| 🔍 **Search** | Full-text search engine based on Elasticsearch |
| 👤 **Users** | Role-based access system, JWT authentication |

## 🛠️ Technology Stack
| Category | Tools |
|----------|-------|
| **Framework** | Django 5.1, Django REST Framework |
| **Database** | PostgreSQL, Redis |
| **Real-time** | Channels, WebSocket |
| **Background Tasks** | Celery, RabbitMQ |
| **Search** | Elasticsearch, django-elasticsearch-dsl |
| **Admin** | Jazzmin Admin Interface |
| **API Docs** | DRF Spectacular (OpenAPI 3.0) |
| **Deployment** | Docker, Nginx, Gunicorn, Uvicorn |
| **Extras** | Pandas, OpenPyXL, Plotly, Axes |

## 🚀 Quick Start
```bash
# Clone repository
git clone https://github.com/Samir-Salihov/Backend-Pytomnik.git
cd Backend-Pytomnik

# Copy environment
cp .env.example .env

# Start all services
docker-compose up -d --build

# Apply migrations
docker-compose exec web python manage.py migrate

# Create admin user
docker-compose exec web python manage.py createsuperuser
```

✅ Admin panel available at: `http://localhost:8000/pytomnic-adminka-cats/`

---

</details>

<details open>
<summary>🇷🇺 Русский</summary>
<br>

## 📋 О проекте
Backend часть системы управления питомником для колледжа. Полнофункциональная административная панель с аналитикой, экспортом, канбан доской и обновлениями в реальном времени.

## ✨ Возможности системы
| Модуль | Описание |
|--------|----------|
| 🎓 **Студенты** | Полное управление профилями, отслеживание уровней, статусы, категории, история изменений |
| 📋 **HR Вызовы** | Система вызовов в отдел кадров с классификацией, файлами вложений и экспортом |
| 📊 **Аналитика** | Интерактивный дашборд с выбором периода, графики и динамические счётчики |
| 📤 **Экспорт** | Генерация отчётов Excel/CSV с настраиваемыми полями |
| 📋 **Канбан** | Канбан доска в реальном времени с drag&drop по WebSocket |
| 🔍 **Поиск** | Полнотекстовый поиск на базе Elasticsearch |
| 👤 **Пользователи** | Система доступа по ролям, JWT аутентификация |

## 🛠️ Стек технологий
| Категория | Инструменты |
|-----------|-------------|
| **Фреймворк** | Django 5.1, Django REST Framework |
| **Базы данных** | PostgreSQL, Redis |
| **Реальное время** | Channels, WebSocket |
| **Фоновые задачи** | Celery, RabbitMQ |
| **Поиск** | Elasticsearch, django-elasticsearch-dsl |
| **Админ панель** | Jazzmin Admin Interface |
| **Документация API** | DRF Spectacular (OpenAPI 3.0) |
| **Деплой** | Docker, Nginx, Gunicorn, Uvicorn |
| **Дополнительно** | Pandas, OpenPyXL, Plotly, Axes |

## 🚀 Быстрый старт
```bash
# Клонировать репозиторий
git clone https://github.com/Samir-Salihov/Backend-Pytomnik.git
cd Backend-Pytomnik

# Скопировать переменные окружения
cp .env.example .env

# Запустить все сервисы
docker-compose up -d --build

# Применить миграции
docker-compose exec web python manage.py migrate

# Создать администратора
docker-compose exec web python manage.py createsuperuser
```

✅ Админ панель доступна по адресу: `http://localhost:8000/pytomnic-adminka-cats/`

---

## 📁 Структура проекта
```
Backend-Pytomnik/
├── apps/
│   ├── students/       # Модуль студентов
│   ├── hr_calls/       # Модуль HR вызовов
│   ├── analytics/      # Аналитика и дашборды
│   ├── export/         # Генерация отчётов
│   ├── kanban/         # Канбан доска
│   ├── search/         # Полнотекстовый поиск
│   └── users/          # Пользователи и авторизация
├── core/               # Основные настройки Django
├── nginx/              # Конфигурация веб-сервера
├── templates/          # Шаблоны админ панели
└── utils/              # Вспомогательные утилиты
```

---

## 🐳 Основные Docker команды
```bash
# Статус контейнеров
docker-compose ps

# Просмотр логов
docker-compose logs -f web

# Войти в контейнер
docker-compose exec web bash

# Остановить всё
docker-compose down

# Сделать бэкап базы
docker-compose exec db pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_$(date +%F).sql
```

---

## 🔐 Безопасность
✅ Все секреты хранятся в переменных окружения  
✅ Защита от брутфорса через Django Axes  
✅ Ролевой доступ ко всем модулям  
✅ Валидация всех входящих данных  
✅ Логирование всех действий пользователей

---

</details>

---

<div align="center">

### 💻 Разработано для внутреннего использования
**Версия 1.0 | Последнее обновление Апрель 2026**

</div>
</div>