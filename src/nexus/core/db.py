"""Настройка подключения к базе данных."""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from nexus.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""

    metadata = MetaData()


# Создание асинхронного движка
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session():
    """Получить асинхронную сессию базы данных."""
    async with async_session_maker() as session:
        yield session


async def create_tables() -> None:
    """Создать все таблицы в базе данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Удалить все таблицы из базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
