"""Конфигурация приложения."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки приложения."""

    # База данных
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/nexus_db",
        alias="DATABASE_URL",
    )
    test_database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5433/nexus_test",
        alias="TEST_DATABASE_URL",
    )

    # API
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")
    debug: bool = Field(True, alias="DEBUG")
    secret_key: str = Field("super-secret-key", alias="SECRET_KEY")

    # Провайдеры
    hackernews_api_url: str = Field(
        "https://hacker-news.firebaseio.com/v0",
        alias="HACKERNEWS_API_URL",
    )
    hn_max_posts: int = Field(30, alias="HN_MAX_POSTS")

    # Имя файла .env и кодировка
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Глобальный экземпляр настроек
settings = Settings()
