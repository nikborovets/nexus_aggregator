"""Главный модуль FastAPI приложения."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import BackgroundTasks, FastAPI, HTTPException

from nexus.core.db import create_tables, get_async_session
from nexus.posts.router import router as posts_router
from nexus.providers.service import ProviderService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Флаг для фоновой задачи
_background_task_running = False


async def aggregate_content_task():
    """Фоновая задача для агрегации контента."""
    global _background_task_running
    
    while _background_task_running:
        try:
            logger.info("Запуск агрегации контента...")
            
            # Получаем сессию для фоновой задачи
            async for session in get_async_session():
                provider_service = ProviderService(session)
                
                # Агрегируем контент из всех провайдеров
                results = await provider_service.aggregate_all_providers()
                
                # ВАЖНО: Коммитимся транзакцию
                await session.commit()
                
                total_new_posts = sum(len(posts) for posts in results.values())
                logger.info(f"Агрегация завершена. Новых постов: {total_new_posts}")
                
                for provider_name, posts in results.items():
                    logger.info(f"  {provider_name}: {len(posts)} новых постов")
                
                break  # Выходим из цикла получения сессии
                
        except Exception as e:
            logger.error(f"Ошибка при агрегации контента: {e}")
        
        # Ожидание перед следующим запуском (30 минут)
        await asyncio.sleep(1800)


async def start_background_aggregation():
    """Запуск фоновой задачи агрегации."""
    global _background_task_running
    
    if not _background_task_running:
        _background_task_running = True
        # Запускаем задачу в фоне
        asyncio.create_task(aggregate_content_task())
        logger.info("Фоновая агрегация контента запущена")


async def stop_background_aggregation():
    """Остановка фоновой задачи агрегации."""
    global _background_task_running
    
    if _background_task_running:
        _background_task_running = False
        logger.info("Фоновая агрегация контента остановлена")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events для приложения."""
    # Startup
    logger.info("Запуск приложения Nexus Aggregator...")
    await create_tables()
    
    # Запуск фоновой агрегации
    await start_background_aggregation()
    
    yield
    
    # Shutdown
    logger.info("Остановка приложения Nexus Aggregator...")
    await stop_background_aggregation()


# Создание приложения
app = FastAPI(
    title="Nexus Aggregator",
    description="Асинхронный агрегатор контента из различных источников",
    version="0.1.0",
    lifespan=lifespan,
)

# Подключение роутеров
app.include_router(posts_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {
        "message": "Nexus Aggregator API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health():
    """Health check эндпоинт."""
    return {
        "status": "ok",
        "background_task_running": _background_task_running
    }


@app.post("/api/v1/aggregate")
async def manual_aggregate(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Ручной запуск агрегации контента."""
    
    async def run_aggregation():
        """Запуск агрегации в фоновой задаче."""
        try:
            logger.info("Ручной запуск агрегации контента...")
            
            async for session in get_async_session():
                provider_service = ProviderService(session)
                results = await provider_service.aggregate_all_providers()
                
                # ВАЖНО: Коммитимся транзакцию
                await session.commit()
                
                total_new_posts = sum(len(posts) for posts in results.values())
                logger.info(f"Ручная агрегация завершена. Новых постов: {total_new_posts}")
                
                break
                
        except Exception as e:
            logger.error(f"Ошибка при ручной агрегации: {e}")
    
    # Добавляем задачу в фон
    background_tasks.add_task(run_aggregation)
    
    return {
        "message": "Агрегация контента запущена в фоновом режиме",
        "status": "started"
    }


@app.get("/api/v1/status")
async def get_status():
    """Получение статуса приложения."""
    return {
        "app_name": "Nexus Aggregator",
        "version": "0.1.0",
        "background_aggregation": _background_task_running,
        "endpoints": {
            "posts": "/api/v1/posts/",
            "manual_aggregate": "/api/v1/aggregate",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/api/v1/debug/aggregate")
async def debug_aggregate():
    """Отладочный эндпоинт для тестирования агрегации."""
    try:
        logger.info("Начинаем отладочную агрегацию...")
        
        async for session in get_async_session():
            provider_service = ProviderService(session)
            results = await provider_service.aggregate_all_providers(limit_per_provider=5)
            
            # ВАЖНО: Коммитимся транзакцию
            await session.commit()
            
            total_posts = sum(len(posts) for posts in results.values())
            logger.info(f"Отладочная агрегация завершена. Постов: {total_posts}")
            
            return {
                "success": True,
                "results": {
                    source: len(posts) for source, posts in results.items()
                },
                "total_posts": total_posts
            }
            
    except Exception as e:
        logger.error(f"Ошибка при отладочной агрегации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка агрегации: {str(e)}") 