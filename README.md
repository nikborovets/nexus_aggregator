# Проект "Nexus": Асинхронный агрегатор контента

## Статус проекта: MVP завершен ✅

Проект прошел все стадии разработки от инициализации до деплоя в Docker. Основная функциональность реализована и протестирована.

## Концепция

FastAPI-сервис, который:
1.  **Собирает** посты из Hacker News и RSS-фидов (`Planet Python`, `RealPython`, `Python Jobs`).
2.  **Нормализует** их в единую модель данных.
3.  **Сохраняет** в PostgreSQL, избегая дубликатов.
4.  **Отдает** контент через REST API с пагинацией и фильтрами.
5.  **Автоматически обновляет** данные каждые 30 минут в фоновом режиме.

## Реализованная архитектура и функциональность

### Структура проекта

Используется `src`-layout с разделением по доменным областям для лучшей масштабируемости.

```
nexus-aggregator/
├── .github/workflows/ci.yml   # CI/CD пайплайн
├── src/
│   └── nexus/
│       ├── main.py              # Точка входа, lifespan, фоновые задачи
│       ├── core/
│       │   ├── config.py        # Конфигурация (Pydantic's BaseSettings)
│       │   └── db.py            # Настройка подключения к БД
│       ├── posts/
│       │   ├── router.py        # API-роутер для постов
│       │   ├── schemas.py       # Pydantic-схемы
│       │   ├── models.py        # SQLAlchemy-модели
│       │   └── service.py       # Бизнес-логика работы с БД
│       └── providers/
│           ├── base.py          # Абстрактный базовый класс провайдера
│           ├── hn.py            # Логика для Hacker News API
│           ├── rss.py           # Логика для парсинга RSS
│           └── service.py       # Сервис-оркестратор провайдеров
│
├── tests/                     # Unit и интеграционные тесты
├── .pre-commit-config.yaml    # Хуки для ruff
├── pyproject.toml             # Зависимости и конфигурация инструментов
├── Dockerfile                 # Многоэтапный Dockerfile для продакшена
└── docker-compose.yml         # Запуск приложения и БД
```

### Ключевые технические решения

- **Асинхронность**: `async/await` используется для всех I/O операций (HTTP-запросы, работа с БД).
- **База данных**: SQLAlchemy 2.0 async с `asyncpg`, идемпотентное сохранение через `ON CONFLICT DO NOTHING`.
- **Фоновые задачи**: Встроенные `lifespan` события и `asyncio.create_task` для периодической агрегации контента без использования тяжелых брокеров вроде Celery.
- **Тестирование**: Трехуровневая система (unit, integration, api) с использованием `pytest`. Интеграционные тесты работают с реальной тестовой БД в Docker.
- **CI/CD**: Пайплайн на GitHub Actions, который запускает тесты для Python 3.13 и 3.12, проверяет форматирование и линтинг (`ruff`), и собирает Docker-образ.
- **Контейнеризация**: Оптимизированный многоэтапный `Dockerfile` и `docker-compose.yml` для легкого запуска всего стека.

### Модели данных

**Pydantic Schema (`schemas.py`)**
```python
class PostResponse(BaseModel):
    id: int
    title: str
    url: HttpUrl
    source: str
    published_at: datetime

    class Config:
        from_attributes = True
```

**SQLAlchemy Model (`models.py`)**
```python
class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(index=True)
    url: Mapped[str] = mapped_column(unique=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

## Как запустить

См. подробное руководство [API_GUIDE.md](API_GUIDE.md).

## Качество кода: Линтинг и Форматирование

В проекте используется `ruff` для форматирования и линтинга кода. Для автоматизации этих проверок настроены **pre-commit хуки**.

### Единая команда для проверки

Команда `uv run pre-commit run --all-files` заменяет ручной запуск `ruff format` и `ruff check`, так как она выполняет все шаги, настроенные в `.pre-commit-config.yaml`. Используйте ее для полной проверки и форматирования всего проекта.

```bash
# Запустить все проверки и исправления для всех файлов
uv run pre-commit run --all-files
```

### Настройка перед первым коммитом

Чтобы хуки работали автоматически перед каждым коммитом, их нужно установить один раз:

```bash
uv run pre-commit install
```

## Потенциальные улучшения (после MVP)

- [ ] **Кэширование**: Добавить Redis для кэширования ответов API.
- [ ] **Аутентификация**: Защитить API с помощью JWT.
- [ ] **Полнотекстовый поиск**: Интегрировать `MeiliSearch` или `Typesense`.
- [ ] **Продвинутые фоновые задачи**: Мигрировать на `arq` для более гибкого управления задачами.
- [ ] **Мониторинг**: Добавить экспорт метрик для Prometheus.
