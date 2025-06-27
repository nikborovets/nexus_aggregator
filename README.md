# Проект "Nexus": Асинхронный агрегатор контента

## Концепция

Создаем FastAPI-сервис, который:
1.  **Собирает** посты из разнородных источников (Hacker News, Reddit, RSS-фиды).
2.  **Нормализует** их в единый формат данных (Pydantic-модель).
3.  **Сохраняет** в базу данных (PostgreSQL с использованием SQLAlchemy 2.0 async).
4.  **Отдает** унифицированный список постов через собственный REST API.
5.  **Обновляет** данные в фоне, чтобы API всегда отдавал свежий контент.

## Ключевые фичи (MVP)

*   Агрегация из 2-3 источников: Hacker News (API), любой RSS-фид.
*   Единая модель поста: `id`, `title`, `url`, `source_name`, `published_at`.
*   Один API-эндпоинт `GET /api/v1/posts` для получения списка постов с пагинацией.
*   Фоновая задача для периодического сбора нового контента.

---

## 1. Структура проекта

Используем `src`-layout и разделение по доменным областям. Это чище и лучше масштабируется, чем разделение по типам файлов (`routers`, `models`).

```
nexus-aggregator/
├── .github/workflows/ci.yml   # CI/CD пайплайн
├── src/
│   └── nexus/
│       ├── __init__.py
│       ├── main.py              # Инициализация FastAPI приложения
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # Глобальная конфигурация (Pydantic's BaseSettings)
│       │   └── db.py            # Настройка подключения к БД (engine, session)
│       │
│       ├── posts/
│       │   ├── __init__.py
│       │   ├── router.py        # API-роутер для постов (/posts)
│       │   ├── schemas.py       # Pydantic-схемы для постов (ввод/вывод)
│       │   ├── models.py        # SQLAlchemy-модели для постов (таблица в БД)
│       │   └── service.py       # Бизнес-логика: работа с постами в БД
│       │
│       └── providers/
│           ├── __init__.py
│           ├── base.py          # Абстрактный базовый класс для провайдеров
│           ├── hn.py            # Логика для Hacker News API
│           ├── rss.py           # Логика для парсинга RSS
│           └── service.py       # Сервис-оркестратор, вызывающий всех провайдеров
│
├── tests/                     # Тесты (структура повторяет src/)
│   ├── conftest.py          # Общие фикстуры (например, test client, db session)
│   ├── posts/
│   │   ├── test_router.py
│   │   └── test_service.py
│   └── providers/
│       ├── test_hn.py
│       └── test_rss.py
│
├── .gitignore
├── .pre-commit-config.yaml    # Конфигурация pre-commit хуков
└── pyproject.toml             # Зависимости, конфигурация ruff, pytest
```

---

## 2. Модели данных (Pydantic & SQLAlchemy)

#### Pydantic Schema (`src/nexus/posts/schemas.py`)
```python
from datetime import datetime
from pydantic import BaseModel, HttpUrl

class PostBase(BaseModel):
    title: str
    url: HttpUrl
    source: str

class PostCreate(PostBase):
    # Данные, которые мы получаем от провайдеров
    published_at: datetime

class PostScheme(PostBase):
    # Данные, которые мы отдаем через API
    id: int
    published_at: datetime

    class Config:
        orm_mode = True # или from_attributes = True для Pydantic v2
```

#### SQLAlchemy Model (`src/nexus/posts/models.py`)
```python
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from nexus.core.db import Base

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, index=True)
    url: Mapped[str] = mapped_column(String, unique=True) # Уникальность по URL
    source: Mapped[str] = mapped_column(String(50), index=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

---

## 3. Философия тестирования

Мы будем использовать три уровня тестов:

1.  **Unit-тесты (модульные):** Тестируем одну маленькую часть (функцию, класс) в полной изоляции. Внешние зависимости, такие как API-запросы (`httpx`) или база данных, **мокаются** (заменяются на заглушки).
2.  **Интеграционные тесты:** Проверяем взаимодействие нескольких компонентов (например, роутер -> сервис -> база данных). Используем **тестовую базу данных**.
3.  **E2E (End-to-End) тесты:** Тестируем полный сценарий работы приложения через его публичный API с помощью `httpx.AsyncClient`.

---

## 4. План разработки (по шагам)

**Шаг 1: Инициализация проекта и окружения**
*   Создать структуру директорий.
*   Инициализировать `uv`: `uv init`.
*   Установить зависимости: `uv pip install "fastapi[all]" sqlalchemy[asyncio] asyncpg httpx feedparser`.
*   Добавить dev-зависимости: `uv pip install -d pytest pytest-asyncio pytest-cov httpx pytest-mock`.
*   Настроить `pyproject.toml` с `ruff` и `pytest`.

**Шаг 2: Настройка ядра (Core) и базовых тестов**
*   Настроить асинхронный `engine` и `sessionmaker` для SQLAlchemy в `src/nexus/core/db.py`.
*   Создать класс настроек Pydantic в `src/nexus/core/config.py`.
*   Создать фикстуру `client` для `pytest` в `tests/conftest.py`.

**Шаг 3: Реализация провайдеров + Unit-тесты**
*   Создать абстрактный класс `BaseProvider` в `src/nexus/providers/base.py`.
*   Реализовать конкретные провайдеры (`HackerNewsProvider`, `RssProvider`).
*   Написать unit-тесты для каждого провайдера, мокая внешние HTTP-запросы.

**Шаг 4: Реализация сервисов + Интеграционные тесты**
*   Реализовать сервисные функции для работы с БД (`posts.service.py`), используя `on_conflict_do_nothing` для идемпотентности.
*   Написать интеграционные тесты для сервисного слоя с использованием временной тестовой БД.
*   Реализовать сервис-оркестратор `providers.service.py`.

**Ша-г 5: Создание API Endpoint + Интеграционные тесты**
*   Создать `APIRouter` в `src/nexus/posts/router.py` с эндпоинтом `GET /`.
*   Написать интеграционные тесты для API, используя `client` и тестовую БД для проверки полного цикла "запрос-ответ".

**Шаг 6: Сборка и фоновые задачи**
*   Собрать все вместе в `src/nexus/main.py`.
*   Реализовать запуск агрегации с помощью `BackgroundTasks` FastAPI.
*   Настроить CI/CD пайплайн в `.github/workflows/ci.yml` для автоматического запуска линтера и тестов.

---

## 5. Потенциальные улучшения (после MVP)

*   **Кэширование**: Добавить Redis для кэширования ответов API.
*   **Аутентификация**: Защитить API с помощью JWT.
*   **Подписки пользователей**: Дать пользователям возможность самим добавлять RSS-фиды.
*   **Полнотекстовый поиск**: Интегрировать `Elasticsearch` или `MeiliSearch`.
*   **Продвинутые фоновые задачи**: Использовать `arq` или `Celery` для более надежного и масштабируемого выполнения фоновых задач по расписанию. 