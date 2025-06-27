"""Конфигурация приложения."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nexus"
    test_database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/nexus_test"

    # App
    debug: bool = False
    secret_key: str = "dev-secret-key-change-in-production"

    # External APIs
    hackernews_api_url: str = "https://hacker-news.firebaseio.com/v0"

    # Background tasks
    aggregation_interval_minutes: int = 30

    class Config:
        """Конфигурация для BaseSettings."""

        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
settings = Settings()
