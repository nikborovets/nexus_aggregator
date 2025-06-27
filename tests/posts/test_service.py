"""Интеграционные тесты для PostService."""

from datetime import datetime, timedelta

import pytest
from nexus.posts.schemas import PostCreate, PostFilter
from nexus.posts.service import PostService


@pytest.mark.integration
class TestPostService:
    """Интеграционные тесты для PostService."""

    @pytest.fixture
    def post_service(self, db_session):
        """Фикстура для создания сервиса постов."""
        return PostService(db_session)

    @pytest.fixture
    def sample_posts(self):
        """Фикстура с примерами постов для тестов."""
        return [
            PostCreate(
                title="Test Post 1",
                url="https://example.com/post1",
                source="test-source",
                published_at=datetime.now() - timedelta(hours=1),
            ),
            PostCreate(
                title="Test Post 2",
                url="https://example.com/post2",
                source="test-source",
                published_at=datetime.now() - timedelta(hours=2),
            ),
            PostCreate(
                title="Another Post",
                url="https://another.com/post",
                source="another-source",
                published_at=datetime.now() - timedelta(hours=3),
            ),
        ]

    async def test_create_posts_success(self, post_service, sample_posts):
        """Тест успешного создания постов."""
        created_posts = await post_service.create_posts(sample_posts)

        assert len(created_posts) == 3
        assert all(post.id is not None for post in created_posts)

        # Проверяем что все посты созданы (порядок может отличаться)
        titles = {post.title for post in created_posts}
        expected_titles = {"Test Post 1", "Test Post 2", "Another Post"}
        assert titles == expected_titles

    async def test_create_posts_empty_list(self, post_service):
        """Тест создания постов с пустым списком."""
        created_posts = await post_service.create_posts([])
        assert created_posts == []

    async def test_create_posts_duplicates(self, post_service, sample_posts):
        """Тест создания постов с дубликатами."""
        # Создаем посты первый раз
        first_batch = await post_service.create_posts(sample_posts)
        assert len(first_batch) == 3

        # Пытаемся создать те же посты еще раз
        second_batch = await post_service.create_posts(sample_posts)

        # Должны получить те же посты (по ID)
        assert len(second_batch) == 3
        first_ids = {post.id for post in first_batch}
        second_ids = {post.id for post in second_batch}
        assert first_ids == second_ids

    async def test_get_posts_pagination(self, post_service, sample_posts):
        """Тест пагинации при получении постов."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Получаем первую страницу
        posts, total = await post_service.get_posts(page=1, size=2)

        assert len(posts) == 2
        assert total == 3

        # Получаем вторую страницу
        posts_page2, total_page2 = await post_service.get_posts(page=2, size=2)

        assert len(posts_page2) == 1
        assert total_page2 == 3

    async def test_get_posts_with_source_filter(self, post_service, sample_posts):
        """Тест фильтрации постов по источнику."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Фильтруем по источнику
        filter_obj = PostFilter(source="test-source")
        posts, total = await post_service.get_posts(filters=filter_obj)

        assert len(posts) == 2
        assert total == 2
        assert all(post.source == "test-source" for post in posts)

    async def test_get_posts_with_search_filter(self, post_service, sample_posts):
        """Тест поиска постов по тексту."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Ищем по заголовку
        filter_obj = PostFilter(search="Another")
        posts, total = await post_service.get_posts(filters=filter_obj)

        assert len(posts) == 1
        assert total == 1
        assert "Another" in posts[0].title

    async def test_get_post_by_id_success(self, post_service, sample_posts):
        """Тест получения поста по ID."""
        # Создаем посты
        created_posts = await post_service.create_posts(sample_posts)

        # Получаем первый пост по ID
        post = await post_service.get_post_by_id(created_posts[0].id)

        assert post is not None
        assert post.id == created_posts[0].id
        assert post.title == created_posts[0].title

    async def test_get_post_by_id_not_found(self, post_service):
        """Тест получения несуществующего поста."""
        post = await post_service.get_post_by_id(99999)
        assert post is None

    async def test_get_posts_by_source(self, post_service, sample_posts):
        """Тест получения постов по источнику."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Получаем посты по источнику
        posts = await post_service.get_posts_by_source("test-source")

        assert len(posts) == 2
        assert all(post.source == "test-source" for post in posts)

    async def test_get_posts_by_source_not_found(self, post_service):
        """Тест получения постов по несуществующему источнику."""
        posts = await post_service.get_posts_by_source("nonexistent-source")
        assert posts == []

    async def test_delete_old_posts(self, post_service, db_session):
        """Тест удаления старых постов."""
        # Создаем старые и новые посты
        old_posts = [
            PostCreate(
                title="Old Post 1",
                url="https://example.com/old1",
                source="test-source",
                published_at=datetime.now() - timedelta(days=35),
            ),
            PostCreate(
                title="Old Post 2",
                url="https://example.com/old2",
                source="test-source",
                published_at=datetime.now() - timedelta(days=40),
            ),
        ]

        new_posts = [
            PostCreate(
                title="New Post",
                url="https://example.com/new",
                source="test-source",
                published_at=datetime.now() - timedelta(days=1),
            ),
        ]

        # Создаем посты
        await post_service.create_posts(old_posts + new_posts)

        # Удаляем старые посты (старше 30 дней)
        deleted_count = await post_service.delete_old_posts(days=30)

        assert deleted_count == 2

        # Проверяем что остался только новый пост
        remaining_posts, total = await post_service.get_posts()
        assert total == 1
        assert remaining_posts[0].title == "New Post"

    async def test_get_source_stats(self, post_service, sample_posts):
        """Тест получения статистики по источникам."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Получаем статистику
        stats = await post_service.get_source_stats()

        assert len(stats) == 2

        # Проверяем статистику для test-source
        test_source_stats = next((s for s in stats if s["source"] == "test-source"), None)
        assert test_source_stats is not None
        assert test_source_stats["total_posts"] == 2
        assert test_source_stats["latest_post"] is not None

        # Проверяем статистику для another-source
        another_source_stats = next((s for s in stats if s["source"] == "another-source"), None)
        assert another_source_stats is not None
        assert another_source_stats["total_posts"] == 1

    async def test_get_posts_ordering(self, post_service, sample_posts):
        """Тест сортировки постов по дате публикации."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Получаем посты
        posts, _ = await post_service.get_posts()

        # Проверяем что посты отсортированы по убыванию даты
        assert len(posts) == 3
        for i in range(len(posts) - 1):
            assert posts[i].published_at >= posts[i + 1].published_at

    async def test_get_posts_page_size_limit(self, post_service, sample_posts):
        """Тест ограничения размера страницы."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Пытаемся получить больше максимального размера
        posts, total = await post_service.get_posts(page=1, size=200)

        # Размер должен быть ограничен до 100
        assert len(posts) == 3  # У нас всего 3 поста
        assert total == 3

    async def test_get_posts_invalid_page(self, post_service, sample_posts):
        """Тест с невалидным номером страницы."""
        # Создаем посты
        await post_service.create_posts(sample_posts)

        # Пытаемся получить с невалидным номером страницы
        posts, total = await post_service.get_posts(page=0, size=10)

        # Должно работать как page=1
        assert len(posts) == 3
        assert total == 3
