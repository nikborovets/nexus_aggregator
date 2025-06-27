"""Провайдер для получения постов из Hacker News."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import ValidationError

from nexus.core.config import settings
from nexus.posts.schemas import PostCreate
from nexus.providers.base import BaseProvider


class HackerNewsProvider(BaseProvider):
    """Провайдер для получения постов из Hacker News API."""

    def __init__(self) -> None:
        """Инициализация провайдера Hacker News."""
        super().__init__("hackernews")
        self.base_url = settings.hackernews_api_url
        self.timeout = 30.0

    async def fetch_posts(self, limit: int = 50) -> List[PostCreate]:
        """
        Получить топ-посты из Hacker News.

        Args:
            limit: Максимальное количество постов для получения

        Returns:
            Список схем PostCreate
        """
        if not await self.is_available():
            return []

        try:
            # Получение ID топ-постов
            top_story_ids = await self._get_top_story_ids()
            if not top_story_ids:
                return []

            # Ограничиваем количество постов
            story_ids = top_story_ids[:limit]

            # Получение детальной информации о постах
            posts = await self._get_posts_details(story_ids)
            return posts

        except Exception as e:
            print(f"Ошибка при получении постов из Hacker News: {e}")
            return []

    async def is_available(self) -> bool:
        """Проверить доступность Hacker News API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/topstories.json")
                return response.status_code == 200
        except Exception:
            return False

    async def _get_top_story_ids(self) -> List[int]:
        """Получить ID топ-постов."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/topstories.json")
            response.raise_for_status()
            return response.json()

    async def _get_posts_details(self, story_ids: List[int]) -> List[PostCreate]:
        """Получить детальную информацию о постах."""
        posts = []
        
        # Создаем семафор для ограничения concurrent запросов
        semaphore = asyncio.Semaphore(10)
        
        async def fetch_single_post(story_id: int) -> Optional[PostCreate]:
            async with semaphore:
                return await self._get_single_post(story_id)

        # Получаем все посты параллельно
        tasks = [fetch_single_post(story_id) for story_id in story_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтруем успешные результаты
        for result in results:
            if isinstance(result, PostCreate):
                posts.append(result)
        
        return posts

    async def _get_single_post(self, story_id: int) -> Optional[PostCreate]:
        """Получить информацию об одном посте."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/item/{story_id}.json")
                response.raise_for_status()
                item_data = response.json()
                
                return self._parse_hn_item(item_data)
        except Exception as e:
            print(f"Ошибка при получении поста {story_id}: {e}")
            return None

    def _parse_hn_item(self, item_data: Dict[str, Any]) -> Optional[PostCreate]:
        """Парсинг данных поста из Hacker News."""
        try:
            # Проверяем обязательные поля
            if not all(key in item_data for key in ["title", "time"]):
                return None

            # URL может отсутствовать (self-posts)
            url = item_data.get("url")
            if not url:
                # Для self-постов используем ссылку на HN
                url = f"https://news.ycombinator.com/item?id={item_data['id']}"

            # Конвертируем timestamp в datetime
            published_at = datetime.fromtimestamp(item_data["time"])

            return PostCreate(
                title=item_data["title"],
                url=url,
                source=self.source_name,
                published_at=published_at,
            )
        except (KeyError, ValueError, ValidationError) as e:
            print(f"Ошибка при парсинге поста: {e}")
            return None