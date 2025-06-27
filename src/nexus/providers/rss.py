"""Провайдер для получения постов из RSS фидов."""

from datetime import datetime
from urllib.parse import urlparse

import feedparser
import httpx
from pydantic import ValidationError

from nexus.posts.schemas import PostCreate
from nexus.providers.base import BaseProvider


class RssProvider(BaseProvider):
    """Провайдер для получения постов из RSS фидов."""

    def __init__(self, rss_url: str, source_name: str | None = None) -> None:
        """
        Инициализация RSS провайдера.

        Args:
            rss_url: URL RSS фида
            source_name: Название источника (опционально)
        """
        if not source_name:
            # Используем домен как название источника
            parsed_url = urlparse(rss_url)
            source_name = parsed_url.netloc.replace("www.", "")

        super().__init__(source_name)
        self.rss_url = rss_url
        self.timeout = 30.0

    async def fetch_posts(self, limit: int = 50) -> list[PostCreate]:
        """
        Получить посты из RSS фида.

        Args:
            limit: Максимальное количество постов для получения

        Returns:
            Список схем PostCreate
        """
        if not await self.is_available():
            return []

        try:
            # Получение RSS контента
            rss_content = await self._fetch_rss_content()
            if not rss_content:
                return []

            # Парсинг RSS
            feed = feedparser.parse(rss_content)

            if not feed.entries:
                return []

            # Конвертация записей в посты
            posts = []
            for entry in feed.entries[:limit]:
                post = self._parse_rss_entry(entry)
                if post:
                    posts.append(post)

            return posts

        except Exception as e:
            print(f"Ошибка при получении постов из RSS {self.rss_url}: {e}")
            return []

    async def is_available(self) -> bool:
        """Проверить доступность RSS фида."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.head(self.rss_url)
                return response.status_code == 200
        except Exception:
            try:
                # Fallback к GET запросу
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(self.rss_url)
                    return response.status_code == 200
            except Exception:
                return False

    async def _fetch_rss_content(self) -> str | None:
        """Получить содержимое RSS фида."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.rss_url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Ошибка при получении RSS контента: {e}")
            return None

    def _parse_rss_entry(self, entry) -> PostCreate | None:
        """
        Парсинг записи RSS в схему PostCreate.

        Args:
            entry: Запись из feedparser

        Returns:
            Схема PostCreate или None при ошибке
        """
        try:
            # Проверяем обязательные поля
            if not hasattr(entry, "title") or not hasattr(entry, "link"):
                return None

            title = entry.title.strip()
            if not title:
                return None

            url = entry.link.strip()
            if not url:
                return None

            # Парсинг даты публикации
            published_at = self._parse_published_date(entry)
            if not published_at:
                # Используем текущее время как fallback
                published_at = datetime.now()

            return PostCreate(
                title=title,
                url=url,
                source=self.source_name,
                published_at=published_at,
            )

        except (ValueError, ValidationError) as e:
            print(f"Ошибка при парсинге RSS записи: {e}")
            return None

    def _parse_published_date(self, entry) -> datetime | None:
        """
        Парсинг даты публикации из RSS записи.

        Args:
            entry: Запись из feedparser

        Returns:
            Datetime объект или None при ошибке
        """
        # Пробуем разные поля для даты
        date_fields = ["published_parsed", "updated_parsed"]

        for field in date_fields:
            if hasattr(entry, field):
                time_struct = getattr(entry, field)
                if time_struct:
                    try:
                        return datetime(*time_struct[:6])
                    except (TypeError, ValueError):
                        continue

        # Fallback к строковым полям
        string_fields = ["published", "updated"]
        for field in string_fields:
            if hasattr(entry, field):
                date_string = getattr(entry, field)
                if date_string:
                    try:
                        # feedparser обычно парсит даты автоматически
                        # но на всякий случай добавим basic parsing
                        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
                        # Конвертируем в naive datetime для совместимости
                        return dt.replace(tzinfo=None)
                    except (ValueError, AttributeError):
                        continue

        return None
