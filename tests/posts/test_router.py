"""Интеграционные тесты для API роутера постов."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from nexus.posts.schemas import PostCreate
from nexus.posts.service import PostService


@pytest.mark.integration
class TestPostsAPI:
    """Тесты API эндпоинтов для постов."""

    @pytest.fixture
    async def sample_posts_in_db(self, db_session: AsyncSession):
        """Создает тестовые посты в базе данных."""
        post_service = PostService(db_session)
        
        sample_posts = [
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
        
        created_posts = await post_service.create_posts(sample_posts)
        return created_posts

    def test_get_posts_success(self, client: TestClient, sample_posts_in_db):
        """Тест успешного получения списка постов."""
        response = client.get("/api/v1/posts/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "posts" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data
        
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["size"] == 3
        assert data["pages"] == 1
        assert len(data["posts"]) == 3
        
        # Проверяем структуру поста
        post = data["posts"][0]
        assert "id" in post
        assert "title" in post
        assert "url" in post
        assert "source" in post
        assert "published_at" in post

    def test_get_posts_pagination(self, client: TestClient, sample_posts_in_db):
        """Тест пагинации при получении постов."""
        # Получаем первую страницу
        response = client.get("/api/v1/posts/?page=1&size=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["pages"] == 2
        assert len(data["posts"]) == 2
        
        # Получаем вторую страницу
        response = client.get("/api/v1/posts/?page=2&size=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3
        assert data["page"] == 2
        assert data["size"] == 1
        assert data["pages"] == 2
        assert len(data["posts"]) == 1

    def test_get_posts_with_source_filter(self, client: TestClient, sample_posts_in_db):
        """Тест фильтрации постов по источнику."""
        response = client.get("/api/v1/posts/?source=test-source")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["posts"]) == 2
        
        # Проверяем что все посты из нужного источника
        for post in data["posts"]:
            assert post["source"] == "test-source"

    def test_get_posts_with_search_filter(self, client: TestClient, sample_posts_in_db):
        """Тест поиска постов по тексту."""
        response = client.get("/api/v1/posts/?search=Another")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["posts"]) == 1
        assert "Another" in data["posts"][0]["title"]

    def test_get_posts_empty_filters(self, client: TestClient, sample_posts_in_db):
        """Тест с пустыми фильтрами."""
        response = client.get("/api/v1/posts/?source=&search=")
        
        assert response.status_code == 200
        data = response.json()
        
        # Должны получить все посты
        assert data["total"] == 3

    def test_get_post_by_id_success(self, client: TestClient, sample_posts_in_db):
        """Тест успешного получения поста по ID."""
        post_id = sample_posts_in_db[0].id
        
        response = client.get(f"/api/v1/posts/{post_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == post_id
        assert "title" in data
        assert "url" in data
        assert "source" in data
        assert "published_at" in data

    def test_get_post_by_id_not_found(self, client: TestClient):
        """Тест получения несуществующего поста."""
        response = client.get("/api/v1/posts/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_posts_by_source_success(self, client: TestClient, sample_posts_in_db):
        """Тест получения постов по источнику."""
        response = client.get("/api/v1/posts/sources/test-source")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        for post in data:
            assert post["source"] == "test-source"

    def test_get_posts_by_source_not_found(self, client: TestClient):
        """Тест получения постов по несуществующему источнику."""
        response = client.get("/api/v1/posts/sources/nonexistent")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 0

    def test_get_posts_by_source_with_limit(self, client: TestClient, sample_posts_in_db):
        """Тест получения постов по источнику с ограничением."""
        response = client.get("/api/v1/posts/sources/test-source?limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1

    def test_get_source_stats(self, client: TestClient, sample_posts_in_db):
        """Тест получения статистики по источникам."""
        response = client.get("/api/v1/posts/stats/sources")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sources" in data
        sources = data["sources"]
        
        assert len(sources) == 2
        
        # Найдем статистику для test-source
        test_source_stats = next(
            (s for s in sources if s["source"] == "test-source"), None
        )
        assert test_source_stats is not None
        assert test_source_stats["total_posts"] == 2

    def test_get_posts_invalid_page(self, client: TestClient):
        """Тест с невалидным номером страницы."""
        response = client.get("/api/v1/posts/?page=0")
        
        assert response.status_code == 422  # Validation error
        
    def test_get_posts_invalid_size(self, client: TestClient):
        """Тест с невалидным размером страницы."""
        response = client.get("/api/v1/posts/?size=200")
        
        assert response.status_code == 422  # Validation error

    def test_api_root_endpoint(self, client: TestClient):
        """Тест корневого эндпоинта."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Nexus Aggregator Test API"
    
    def test_health_endpoint(self, client: TestClient):
        """Тест health check эндпоинта."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "background_task_running" in data
    
    def test_status_endpoint(self, client: TestClient):
        """Тест эндпоинта статуса приложения."""
        response = client.get("/api/v1/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert data["app_name"] == "Nexus Aggregator"
        assert "version" in data
        assert "background_aggregation" in data
        assert "endpoints" in data
        
        endpoints = data["endpoints"]
        assert "posts" in endpoints
        assert "manual_aggregate" in endpoints
        assert "health" in endpoints
        assert "docs" in endpoints
    
    def test_manual_aggregate_endpoint(self, client: TestClient):
        """Тест эндпоинта ручной агрегации."""
        response = client.post("/api/v1/aggregate")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "started" 