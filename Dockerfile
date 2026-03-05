# Stage 1: Builder
FROM python:3.12-slim as builder

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Устанавливаем только runtime зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем Python зависимости из builder
COPY --from=builder /root/.local /root/.local

# Копируем проект
COPY . .

# Устанавливаем PATH
ENV PATH=/root/.local/bin:$PATH

# Создаём директории для логов, статики и медиа
RUN mkdir -p /app/logs /app/staticfiles /app/media

# Открываем порт
EXPOSE 8000

# Точка входа для миграций и запуска сервера
# Сделаем entrypoint исполняемым (нужен в runtime)
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "1800", "--graceful-timeout", "120", "core.asgi:application"]