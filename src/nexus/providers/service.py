"""Сервис-оркестратор для работы с провайдерами контента."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from nexus.posts.models import Post
from nexus.posts.schemas import PostCreate
from nexus.posts.service import PostService
from nexus.providers.base import BaseProvider
from nexus.providers.hn import HackerNewsProvider
from nexus.providers.rss import RssProvider


class ProvidersService:
    """Сервис для управления всеми провайдерами контента."""

    def __init__(self) -> None:
        """Инициализация сервиса провайдеров."""
        self.providers: list[BaseProvider] = []
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Инициализация всех провайдеров."""
        # Добавляем Hacker News провайдер
        self.providers.append(HackerNewsProvider())

        # Добавляем несколько RSS провайдеров
        rss_feeds = [
            ("https://www.python.org/jobs/feed/rss/", "python-jobs"),
            ("https://realpython.com/atom.xml", "realpython"),
            ("https://planetpython.org/rss20.xml", "planet-python"),
        ]

        for rss_url, source_name in rss_feeds:
            self.providers.append(RssProvider(rss_url, source_name))

    def add_provider(self, provider: BaseProvider) -> None:
        """
        Добавить провайдер в список.

        Args:
            provider: Экземпляр провайдера
        """
        if provider not in self.providers:
            self.providers.append(provider)

    def remove_provider(self, provider: BaseProvider) -> None:
        """
        Удалить провайдер из списка.

        Args:
            provider: Экземпляр провайдера
        """
        if provider in self.providers:
            self.providers.remove(provider)

    async def get_available_providers(self) -> list[BaseProvider]:
        """
        Получить список доступных провайдеров.

        Returns:
            Список доступных провайдеров
        """
        available_providers = []

        # Проверяем доступность всех провайдеров параллельно
        availability_tasks = [
            self._check_provider_availability(provider) for provider in self.providers
        ]

        results = await asyncio.gather(*availability_tasks, return_exceptions=True)

        for provider, is_available in zip(self.providers, results, strict=False):
            if isinstance(is_available, bool) and is_available:
                available_providers.append(provider)

        return available_providers

    async def _check_provider_availability(self, provider: BaseProvider) -> bool:
        """
        Проверить доступность провайдера.

        Args:
            provider: Провайдер для проверки

        Returns:
            True если провайдер доступен
        """
        try:
            return await provider.is_available()
        except Exception as e:
            print(f"Ошибка при проверке провайдера {provider.source_name}: {e}")
            return False

    async def fetch_all_posts(self, limit_per_provider: int = 20) -> list[PostCreate]:
        """
        Получить посты от всех доступных провайдеров.

        Args:
            limit_per_provider: Лимит постов на провайдер

        Returns:
            Объединенный список постов от всех провайдеров
        """
        available_providers = await self.get_available_providers()

        if not available_providers:
            print("Нет доступных провайдеров")
            return []

        print(f"Найдено {len(available_providers)} доступных провайдеров")

        # Получаем посты от всех провайдеров параллельно
        fetch_tasks = [
            self._fetch_from_provider(provider, limit_per_provider)
            for provider in available_providers
        ]

        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Объединяем результаты
        all_posts = []
        for provider, posts in zip(available_providers, results, strict=False):
            if isinstance(posts, list):
                all_posts.extend(posts)
                print(f"Получено {len(posts)} постов от {provider.source_name}")
            else:
                print(f"Ошибка при получении постов от {provider.source_name}: {posts}")

        # Удаляем дубликаты по URL
        unique_posts = self._remove_duplicates(all_posts)

        print(f"Всего получено {len(all_posts)} постов, уникальных: {len(unique_posts)}")
        return unique_posts

    async def _fetch_from_provider(self, provider: BaseProvider, limit: int) -> list[PostCreate]:
        """
        Получить посты от конкретного провайдера.

        Args:
            provider: Провайдер
            limit: Лимит постов

        Returns:
            Список постов
        """
        try:
            return await provider.fetch_posts(limit)
        except Exception as e:
            print(f"Ошибка при получении постов от {provider.source_name}: {e}")
            return []

    def _remove_duplicates(self, posts: list[PostCreate]) -> list[PostCreate]:
        """
        Удалить дубликаты постов по URL.

        Args:
            posts: Список постов

        Returns:
            Список уникальных постов
        """
        seen_urls = set()
        unique_posts = []

        for post in posts:
            url = str(post.url)
            if url not in seen_urls:
                seen_urls.add(url)
                unique_posts.append(post)

        return unique_posts

    async def fetch_from_source(self, source_name: str, limit: int = 50) -> list[PostCreate]:
        """
        Получить посты от конкретного источника.

        Args:
            source_name: Название источника
            limit: Лимит постов

        Returns:
            Список постов от указанного источника
        """
        provider = self._get_provider_by_source(source_name)
        if not provider:
            print(f"Провайдер для источника '{source_name}' не найден")
            return []

        if not await provider.is_available():
            print(f"Провайдер '{source_name}' недоступен")
            return []

        return await provider.fetch_posts(limit)

    def _get_provider_by_source(self, source_name: str) -> BaseProvider | None:
        """
        Найти провайдер по названию источника.

        Args:
            source_name: Название источника

        Returns:
            Провайдер или None если не найден
        """
        for provider in self.providers:
            if provider.source_name == source_name:
                return provider
        return None

    def get_provider_stats(self) -> dict[str, dict[str, str]]:
        """
        Получить информацию о всех провайдерах.

        Returns:
            Словарь с информацией о провайдерах
        """
        stats = {}
        for provider in self.providers:
            stats[provider.source_name] = {
                "type": provider.__class__.__name__,
                "status": "unknown",  # Статус определяется асинхронно
            }

            # Добавляем специфичную информацию для RSS провайдеров
            if isinstance(provider, RssProvider):
                stats[provider.source_name]["rss_url"] = provider.rss_url

        return stats


class ProviderService:
    """Сервис для агрегации контента с сохранением в базу данных."""

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Инициализация сервиса.

        Args:
            db_session: Сессия базы данных
        """
        self.db_session = db_session
        self.post_service = PostService(db_session)
        self.providers_service = ProvidersService()

    async def aggregate_all_providers(self, limit_per_provider: int = 20) -> dict[str, list[Post]]:
        """
        Агрегация контента от всех провайдеров с сохранением в БД.

        Args:
            limit_per_provider: Лимит постов на провайдер

        Returns:
            Словарь с результатами агрегации {источник: [новые_посты]}
        """
        print(f"[DEBUG] Начинаем агрегацию с лимитом {limit_per_provider} постов на провайдер")

        # Получаем посты от всех провайдеров
        all_posts = await self.providers_service.fetch_all_posts(limit_per_provider)
        print(f"[DEBUG] Получено {len(all_posts)} постов от провайдеров")

        if not all_posts:
            print("[DEBUG] Нет постов для сохранения")
            return {}

        # Сохраняем посты в базу данных
        print(f"[DEBUG] Сохраняем {len(all_posts)} постов в базу данных...")
        try:
            saved_posts = await self.post_service.create_posts(all_posts)
            print(f"[DEBUG] Успешно сохранено {len(saved_posts)} постов")
        except Exception as e:
            print(f"[ERROR] Ошибка при сохранении постов: {e}")
            return {}

        # Группируем сохраненные посты по источникам
        results = {}
        for post in saved_posts:
            if post.source not in results:
                results[post.source] = []
            results[post.source].append(post)

        print(
            f"[DEBUG] Результат агрегации: {[(source, len(posts)) for source, posts in results.items()]}"
        )
        return results

    async def aggregate_from_source(self, source_name: str, limit: int = 50) -> list[Post]:
        """
        Агрегация контента от конкретного источника с сохранением в БД.

        Args:
            source_name: Название источника
            limit: Лимит постов

        Returns:
            Список сохраненных постов
        """
        # Получаем посты от конкретного источника
        posts = await self.providers_service.fetch_from_source(source_name, limit)

        if not posts:
            return []

        # Сохраняем в базу данных
        return await self.post_service.create_posts(posts)

    async def get_provider_stats(self) -> dict[str, dict[str, str]]:
        """
        Получить статистику провайдеров.

        Returns:
            Словарь со статистикой провайдеров
        """
        # Получаем базовую статистику
        stats = self.providers_service.get_provider_stats()

        # Добавляем информацию о доступности
        available_providers = await self.providers_service.get_available_providers()
        available_names = {provider.source_name for provider in available_providers}

        for source_name in stats:
            stats[source_name]["available"] = source_name in available_names

        return stats
