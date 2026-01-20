# Используем официальный Python 3.12 slim (лёгкий и быстрый)
FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем только файлы зависимостей (ускоряет кэш)
COPY requirements.txt ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Собираем статику (если нужно)
RUN python manage.py collectstatic --noinput

# Открываем порт (gunicorn будет слушать 8000)
EXPOSE 8000


CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]