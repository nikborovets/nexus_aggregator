"""Конфигурация тестов."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from nexus.core.db import Base, get_async_session
from nexus.posts.router import router as posts_router


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Создаем тестовый движок БД - SQLite в памяти
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True,
)

# Создаем session maker для тестов
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session")
async def setup_test_db():
    """Создание тестовой базы данных."""
    # Создаем все таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Очищаем таблицы после тестов
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_test_db) -> AsyncGenerator[AsyncSession, None]:
    """Создание сессии базы данных для тестов с откатом транзакций."""
    async with TestSessionLocal() as session:
        # Начинаем транзакцию
        transaction = await session.begin()
        
        try:
            yield session
        finally:
            # Откатываем транзакцию после каждого теста
            await transaction.rollback()


# Создаем отдельное приложение для тестов без lifespan events
def create_test_app() -> FastAPI:
    """Создание тестового FastAPI приложения."""
    app = FastAPI(
        title="Nexus Aggregator Test",
        description="Тестовое приложение без lifespan events",
        version="0.1.0",
    )
    
    # Подключение роутеров
    app.include_router(posts_router, prefix="/api/v1")
    
    @app.get("/")
    async def root():
        """Корневой эндпоинт."""
        return {"message": "Nexus Aggregator Test API"}
    
    @app.get("/health")
    async def health():
        """Health check эндпоинт."""
        return {
            "status": "ok",
            "background_task_running": False
        }
    
    @app.get("/api/v1/status")
    async def get_status():
        """Получение статуса приложения."""
        return {
            "app_name": "Nexus Aggregator",
            "version": "0.1.0", 
            "background_aggregation": False,
            "endpoints": {
                "posts": "/api/v1/posts/",
                "manual_aggregate": "/api/v1/aggregate",
                "health": "/health",
                "docs": "/docs"
            }
        }
    
    @app.post("/api/v1/aggregate")
    async def manual_aggregate():
        """Ручной запуск агрегации контента (тестовая версия)."""
        return {
            "message": "Агрегация контента запущена в фоновом режиме",
            "status": "started"
        }
    
    return app


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """HTTP клиент для тестирования API."""
    
    # Создаем тестовое приложение
    test_app = create_test_app()
    
    # Переопределяем зависимость для получения тестовой сессии
    async def override_get_db():
        yield db_session
    
    # Переопределяем зависимость
    test_app.dependency_overrides[get_async_session] = override_get_db
    
    try:
        # Используем стандартный TestClient
        with TestClient(test_app) as test_client:
            yield test_client
    finally:
        # Очищаем переопределения зависимостей
        test_app.dependency_overrides.clear() 