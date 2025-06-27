"""Сервис для работы с постами в базе данных."""

from typing import List, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nexus.posts.models import Post
from nexus.posts.schemas import PostCreate, PostFilter, PostResponse


class PostService:
    """Сервис для работы с постами."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация сервиса."""
        self.session = session

    async def create_posts(self, posts: List[PostCreate]) -> List[PostResponse]:
        """
        Создать посты в базе данных с обработкой дубликатов.

        Args:
            posts: Список схем PostCreate

        Returns:
            Список созданных постов
        """
        if not posts:
            return []

        try:
            # Подготавливаем данные для вставки
            posts_data = [
                {
                    "title": post.title,
                    "url": str(post.url),
                    "source": post.source,
                    "published_at": post.published_at,
                }
                for post in posts
            ]

            # Используем ON CONFLICT DO NOTHING для идемпотентности
            stmt = insert(Post).values(posts_data)
            stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
            
            await self.session.execute(stmt)
            # В тестах транзакция управляется фикстурой
            # В продакшене commit будет вызван в API слое
            await self.session.flush()

            # Получаем созданные посты по URL
            urls = [str(post.url) for post in posts]
            result = await self.session.execute(
                select(Post).where(Post.url.in_(urls))
            )
            created_posts = result.scalars().all()

            return [
                PostResponse.model_validate(post) for post in created_posts
            ]

        except Exception as e:
            print(f"Ошибка при создании постов: {e}")
            return []

    async def get_posts(
        self,
        page: int = 1,
        size: int = 50,
        filters: Optional[PostFilter] = None,
    ) -> tuple[List[PostResponse], int]:
        """
        Получить список постов с пагинацией и фильтрацией.

        Args:
            page: Номер страницы (начиная с 1)
            size: Размер страницы
            filters: Фильтры для поиска

        Returns:
            Tuple из списка постов и общего количества
        """
        # Валидация параметров
        page = max(1, page)
        size = min(max(1, size), 100)  # Ограничиваем размер страницы

        # Базовый запрос
        query = select(Post)
        count_query = select(func.count(Post.id))

        # Применяем фильтры
        if filters:
            where_conditions = []

            if filters.source:
                where_conditions.append(Post.source == filters.source)

            if filters.search:
                search_term = f"%{filters.search}%"
                where_conditions.append(
                    or_(
                        Post.title.ilike(search_term),
                        Post.url.ilike(search_term),
                    )
                )

            if where_conditions:
                filter_condition = and_(*where_conditions)
                query = query.where(filter_condition)
                count_query = count_query.where(filter_condition)

        # Получаем общее количество
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Применяем сортировку, пагинацию и выполняем запрос
        query = (
            query.order_by(desc(Post.published_at))
            .offset((page - 1) * size)
            .limit(size)
        )

        result = await self.session.execute(query)
        posts = result.scalars().all()

        return (
            [PostResponse.model_validate(post) for post in posts],
            total,
        )

    async def get_post_by_id(self, post_id: int) -> Optional[PostResponse]:
        """
        Получить пост по ID.

        Args:
            post_id: ID поста

        Returns:
            Схема PostResponse или None если не найден
        """
        result = await self.session.execute(
            select(Post).where(Post.id == post_id)
        )
        post = result.scalar_one_or_none()

        if not post:
            return None

        return PostResponse.model_validate(post)

    async def get_posts_by_source(
        self, source: str, limit: int = 50
    ) -> List[PostResponse]:
        """
        Получить посты из конкретного источника.

        Args:
            source: Название источника
            limit: Максимальное количество постов

        Returns:
            Список постов из источника
        """
        limit = min(max(1, limit), 100)

        result = await self.session.execute(
            select(Post)
            .where(Post.source == source)
            .order_by(desc(Post.published_at))
            .limit(limit)
        )
        posts = result.scalars().all()

        return [PostResponse.model_validate(post) for post in posts]

    async def delete_old_posts(self, days: int = 30) -> int:
        """
        Удалить старые посты.

        Args:
            days: Количество дней, после которых посты считаются старыми

        Returns:
            Количество удаленных постов
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)

        result = await self.session.execute(
            select(func.count(Post.id)).where(Post.published_at < cutoff_date)
        )
        count_to_delete = result.scalar() or 0

        if count_to_delete > 0:
            await self.session.execute(
                Post.__table__.delete().where(Post.published_at < cutoff_date)
            )
            await self.session.flush()

        return count_to_delete

    async def get_source_stats(self) -> List[dict]:
        """
        Получить статистику по источникам.

        Returns:
            Список со статистикой по каждому источнику
        """
        result = await self.session.execute(
            select(
                Post.source,
                func.count(Post.id).label("total_posts"),
                func.max(Post.published_at).label("latest_post"),
            )
            .group_by(Post.source)
            .order_by(desc("total_posts"))
        )

        stats = []
        for row in result:
            stats.append({
                "source": row.source,
                "total_posts": row.total_posts,
                "latest_post": row.latest_post,
            })

        return stats 