# Nexus Aggregator - Руководство по API v0.1.0

## Описание

Nexus Aggregator - это асинхронный веб-сервис на FastAPI для агрегации контента из разных источников (Hacker News, RSS-фиды). Приложение собирает посты, нормализует их в единый формат и предоставляет REST API для получения данных, а также автоматически обновляет контент в фоновом режиме.

## Технологический стек

- **Backend**: FastAPI + Python 3.13 / 3.12
- **База данных**: PostgreSQL с async SQLAlchemy 2.0
- **Тестирование**: pytest, SQLite (для unit-тестов), PostgreSQL (для интеграционных)
- **HTTP клиент**: httpx
- **Парсинг RSS**: feedparser
- **Управление зависимостями и окружением**: uv
- **CI/CD**: GitHub Actions
- **Контейнеризация**: Docker & Docker Compose

## Установка и запуск

### 1. Требования

- Python 3.13+
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose

### 2. Запуск с помощью Docker Compose (Рекомендуемый способ)

Этот способ поднимает и приложение, и базу данных PostgreSQL.

```bash
# Клонировать репозиторий
git clone <repository-url>
cd nexus-aggregator

# Запустить сервисы
docker-compose up --build
```

- **API будет доступен**: `http://localhost:8000`
- **Документация Swagger UI**: `http://localhost:8000/docs`
- **Документация ReDoc**: `http://localhost:8000/redoc`
- **База данных PostgreSQL**: `localhost:5432`

### 3. Ручной запуск для разработки

```bash
# 1. Запустить базу данных
docker-compose up -d db

# 2. Установить зависимости
uv venv
source .venv/bin/activate
# Установить все зависимости, включая dev-инструменты (pytest, ruff, pre-commit)
uv pip install -e ".[dev]"

# 3. Создать .env файл (если еще не создан)
echo "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/nexus_db" > .env
echo "DEBUG=true" >> .env

# 4. Запустить приложение
uv run uvicorn src.nexus.main:app --reload
uv run uvicorn src.nexus.main:app --host 0.0.0.0 --port 8000 --reload
```

## Документация API

- **Базовый URL**: `/api/v1`

### Эндпоинты для получения данных

#### 1. Получение списка постов

Получает пагинированный список всех постов.

`GET /posts/`

**Параметры запроса:**
- `page` (int, optional): Номер страницы (по умолчанию: 1)
- `size` (int, optional): Размер страницы (по умолчанию: 20, max: 100)
- `source` (string, optional): Фильтр по источнику (например, `hackernews`)
- `search` (string, optional): Поиск по заголовку и URL

**Пример (curl):**
```bash
curl "http://localhost:8000/api/v1/posts/?page=1&size=5&source=hackernews"
```

**Пример ответа:**
```json
{
  "posts": [
    {
      "title": "A Brief History of Children Sent Through the Mail",
      "url": "https://www.smithsonianmag.com/...",
      "source": "hackernews",
      "id": 399,
      "published_at": "2025-06-27T20:12:00Z"
    }
  ],
  "total": 21,
  "page": 1,
  "size": 5,
  "pages": 5
}
```

#### 2. Получение поста по ID

`GET /posts/{post_id}`

**Пример (curl):**
```bash
curl "http://localhost:8000/api/v1/posts/399"
```

#### 3. Получение постов по источнику

`GET /posts/sources/{source_name}`

**Параметры запроса:**
- `limit` (int, optional): Лимит постов (по умолчанию: 50, max: 100)

**Пример (curl):**
```bash
curl "http://localhost:8000/api/v1/posts/sources/python-jobs?limit=3"
```

#### 4. Статистика по источникам

`GET /posts/stats/sources`

**Пример (curl):**
```bash
curl "http://localhost:8000/api/v1/posts/stats/sources"
```
**Пример ответа:**
```json
{
  "sources": [
    { "source": "hackernews", "total_posts": 21, "latest_post": "..." },
    { "source": "python-jobs", "total_posts": 20, "latest_post": "..." }
  ]
}
```

### Эндпоинты для управления и мониторинга

#### 1. Ручной запуск агрегации

Запускает агрегацию в фоновом режиме.

`POST /aggregate`

**Пример (curl):**
```bash
curl -X POST "http://localhost:8000/api/v1/aggregate"
```
**Ответ:**
```json
{
  "message": "Агрегация контента запущена в фоновом режиме",
  "status": "started"
}
```

#### 2. Статус приложения

`GET /status`

**Ответ:**
```json
{
  "app_name": "Nexus Aggregator",
  "version": "0.1.0",
  "background_aggregation": true,
  "endpoints": { ... }
}
```

#### 3. Health Check

`GET /health` (находится в корне, не в `/api/v1`)

**Ответ:**
```json
{
  "status": "ok",
  "background_task_running": true
}
```

#### 4. Отладочная агрегация

Синхронно запускает агрегацию и возвращает результат.

`GET /debug/aggregate`

**Пример (curl):**
```bash
curl "http://localhost:8000/api/v1/debug/aggregate"
```

## Тестирование

```bash
# Запуск всех тестов
uv run pytest

# С отчетом о покрытии
uv run pytest --cov=src --cov-report=html
```

## CI/CD

Проект использует GitHub Actions для автоматического тестирования, линтинга и сборки Docker-образа при каждом коммите в ветку `main`. Конфигурация находится в `.github/workflows/ci.yml`.

## Примеры использования

### Python с httpx

```python
import httpx
import asyncio

async def get_posts():
    async with httpx.AsyncClient() as client:
        # Получение последних постов
        response = await client.get(
            "http://localhost:8000/api/v1/posts/",
            params={"page": 1, "size": 10}
        )
        posts = response.json()

        # Поиск постов по ключевому слову
        response = await client.get(
            "http://localhost:8000/api/v1/posts/",
            params={"search": "AI", "size": 5}
        )
        ai_posts = response.json()

        return posts, ai_posts

# Запуск
posts, ai_posts = asyncio.run(get_posts())
```

### JavaScript/TypeScript

```javascript
// Получение постов из Hacker News
async function getHackerNewsPosts() {
  const response = await fetch(
    'http://localhost:8000/api/v1/posts/sources/hackernews?limit=20'
  );
  const posts = await response.json();
  return posts;
}

// Поиск постов
async function searchPosts(query) {
  const response = await fetch(
    `http://localhost:8000/api/v1/posts/?search=${encodeURIComponent(query)}`
  );
  const results = await response.json();
  return results;
}
```

### curl примеры

```bash
# Получение последних 5 постов
curl "http://localhost:8000/api/v1/posts/?size=5"

# Поиск постов с "Python" в заголовке
curl "http://localhost:8000/api/v1/posts/?search=Python"

# Получение статистики
curl "http://localhost:8000/api/v1/posts/stats/sources"

# Получение постов из RSS фидов
curl "http://localhost:8000/api/v1/posts/sources/rss-feed"
```

## Разработка

### Структура проекта

```
