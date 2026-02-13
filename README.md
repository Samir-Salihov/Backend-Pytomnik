# pytomnic

Backend проект,

## Перевод на PostgreSQL и бэкапы

1. Настройка Docker (Postgres в контейнере)

- Убедитесь, что в `.env` заданы переменные:
  - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST=db`, `POSTGRES_PORT=5432`

- Запуск стека:

```bash
docker-compose up -d --build
```

2. Миграция данных (если у вас был `core/db.sqlite3`)

- Если вы уже перенесли данные в Postgres, удалите `core/db.sqlite3` после бэкапа (см. пункт 4).

3. Регулярный бэкап Postgres (рекомендация)

- На хосте или CI: делайте дамп базы командой:

```bash
docker-compose exec db pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_postgres_$(date +%F).sql
```

- Храните дампы в надёжном месте (облачное хранилище, отдельный диск) и держите ротацию (например, 30 дней).

4. Нужно ли хранить `db.sqlite3`?

- После успешной миграции и проверки данных `db.sqlite3` можно удалить из репозитория и локального проекта. SQLite не нужен в production.
- Рекомендация: перед удалением сохраните локальную копию на случай отката, затем удалите и добавьте в `.gitignore`.

5. Быстрая проверка целостности после миграции

- Проверьте количество пользователей и ключевых таблиц:

```bash
docker-compose exec db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT count(*) FROM users_user;"
```

6. Автоматизация бэкапов (идея)

- Завести cron job на хосте или GitHub Actions, который каждый день выполняет `pg_dump`, загружает дамп в S3/Drive и удаляет старые файлы — простая и надёжная схема.
  - GitHub Actions workflow: запускать `docker-compose run --rm db pg_dump ...` и сохранять артефакт или загружать в облако.

7. Вопросы безопасности

- Никогда не коммитите реальные пароли в `.env` в публичные репозитории. Храните секреты в менеджере секретов.

## Полезные Docker команды

Ниже — краткая шпаргалка по командам, которыми вы будете пользоваться чаще всего при работе через Docker.

```bash
# Поднять стек (создать/пересобрать образы и запустить в фоне)
docker-compose up -d --build

# Поднять стек без пересборки (быстро)
docker-compose up -d

# Остановить контейнеры (сохранить их состояние)
docker-compose stop

# Запустить остановленные контейнеры
docker-compose start

# Перезапустить сервис(ы)
docker-compose restart
docker-compose restart web

# Посмотреть статус контейнеров
docker-compose ps

# Смотреть логи (реальное время)
docker-compose logs -f web
docker-compose logs -f db

# Попасть в shell контейнера web
docker-compose exec web bash

# Выполнить Django команды внутри web
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
docker-compose exec web python manage.py createsuperuser

# Копировать файл из хоста в контейнер
docker cp C:\путь\к\файлу pytomnic_web:/tmp/

# Бэкап Postgres (создаёт файл дампа на хосте)
docker-compose exec db pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_postgres_$(date +%F).sql

# Остановить и удалить контейнеры/сеть (тома сохраняются)
docker-compose down

# Остановить и удалить контейнеры + тома данных (ОСТОРОЖНО)
docker-compose down -v
```

Совет: не удаляйте том `postgres_data`, пока не убедитесь, что у вас есть рабочий дамп базы.
