"""Базовый класс для всех провайдеров контента."""

from abc import ABC, abstractmethod
from typing import List

from nexus.posts.schemas import PostCreate


class BaseProvider(ABC):
    """Абстрактный базовый класс для провайдеров контента."""

    def __init__(self, source_name: str) -> None:
        """Инициализация провайдера."""
        self.source_name = source_name

    @abstractmethod
    async def fetch_posts(self, limit: int = 50) -> List[PostCreate]:
        """
        Получить список постов от провайдера.

        Args:
            limit: Максимальное количество постов для получения

        Returns:
            Список схем PostCreate
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Проверить доступность провайдера.

        Returns:
            True если провайдер доступен, False иначе
        """
        pass 