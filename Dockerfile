# Используем официальный Python образ
FROM python:3.11-slim as builder

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Создаем виртуальное окружение и устанавливаем зависимости
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -e .

# Продакшн стадия
FROM python:3.11-slim

# Устанавливаем системные зависимости для продакшна
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для приложения
RUN groupadd -r nexus && useradd -r -g nexus nexus

# Создаем рабочую директорию
WORKDIR /app

# Копируем виртуальное окружение из builder стадии
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем исходный код
COPY --chown=nexus:nexus src/ ./src/

# Переключаемся на пользователя nexus
USER nexus

# Открываем порт
EXPOSE 8000

# Настройка переменных окружения
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Команда запуска
CMD ["uvicorn", "nexus.main:app", "--host", "0.0.0.0", "--port", "8000"] 