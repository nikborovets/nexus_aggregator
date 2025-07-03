# Используем последнюю версию Python образа
FROM python:3.13-slim AS builder

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Устанавливаем системные зависимости с обновлениями безопасности
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    gcc \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости в системный Python
RUN uv pip install -e . --system

# Новый этап для тестирования
FROM builder AS test
# Копируем файлы проекта еще раз, так как они нужны для uv sync
COPY pyproject.toml uv.lock ./
# Устанавливаем dev-зависимости поверх production
RUN uv sync --dev --system

# --- Production Stage ---
# Наследуемся от базового чистого образа, а не от test,
# чтобы в итоговый образ не попали dev-зависимости.
FROM python:3.13-slim

# Устанавливаем системные зависимости для продакшна с обновлениями безопасности
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Создаем пользователя для приложения
RUN groupadd -r nexus && useradd -r -g nexus nexus

# Создаем рабочую директорию
WORKDIR /app

# Копируем установленные пакеты из builder стадии
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

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
