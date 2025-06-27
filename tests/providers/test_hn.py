"""Unit-тесты для HackerNewsProvider."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from nexus.providers.hn import HackerNewsProvider


@pytest.mark.unit
class TestHackerNewsProvider:
    """Тесты для HackerNewsProvider."""

    @pytest.fixture
    def provider(self):
        """Фикстура для создания провайдера."""
        return HackerNewsProvider()

    @pytest.fixture
    def mock_story_data(self):
        """Мок данные поста из HN API."""
        return {
            "id": 123456,
            "title": "Test Post Title",
            "url": "https://example.com/test",
            "time": 1640995200,  # 2022-01-01 00:00:00
            "type": "story",
        }

    @pytest.fixture
    def mock_story_ids(self):
        """Мок список ID постов."""
        return [123456, 123457, 123458]

    async def test_is_available_success(self, provider):
        """Тест успешной проверки доступности API."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await provider.is_available()
            assert result is True

    async def test_is_available_failure(self, provider):
        """Тест неуспешной проверки доступности API."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
                "Connection error"
            )

            result = await provider.is_available()
            assert result is False

    @respx.mock
    async def test_get_top_story_ids_success(self, provider, mock_story_ids):
        """Тест успешного получения ID топ-постов."""
        respx.get(f"{provider.base_url}/topstories.json").mock(
            return_value=Response(200, json=mock_story_ids)
        )

        result = await provider._get_top_story_ids()
        assert result == mock_story_ids

    async def test_parse_hn_item_success(self, provider, mock_story_data):
        """Тест успешного парсинга поста из HN."""
        result = provider._parse_hn_item(mock_story_data)

        assert result is not None
        assert result.title == "Test Post Title"
        assert str(result.url) == "https://example.com/test"
        assert result.source == "hackernews"
        assert result.published_at == datetime.fromtimestamp(1640995200)

    async def test_parse_hn_item_self_post(self, provider):
        """Тест парсинга self-поста (без URL)."""
        story_data = {
            "id": 123456,
            "title": "Ask HN: Self Post",
            "time": 1640995200,
            "type": "story",
            # "url" отсутствует
        }

        result = provider._parse_hn_item(story_data)

        assert result is not None
        assert result.title == "Ask HN: Self Post"
        assert str(result.url) == "https://news.ycombinator.com/item?id=123456"
        assert result.source == "hackernews"

    async def test_parse_hn_item_missing_required_fields(self, provider):
        """Тест парсинга поста с отсутствующими обязательными полями."""
        story_data = {
            "id": 123456,
            # "title" отсутствует
            "url": "https://example.com/test",
            # "time" отсутствует
        }

        result = provider._parse_hn_item(story_data)
        assert result is None

    async def test_fetch_posts_success(self, provider, mock_story_ids, mock_story_data):
        """Тест успешного получения постов."""
        with (
            patch.object(provider, "is_available", return_value=True),
            patch.object(provider, "_get_top_story_ids", return_value=mock_story_ids),
            patch.object(provider, "_get_posts_details") as mock_get_details,
        ):
            mock_post_create = AsyncMock()
            mock_post_create.title = "Test Post"
            mock_get_details.return_value = [mock_post_create]

            result = await provider.fetch_posts(limit=10)

            assert len(result) == 1
            assert result[0] == mock_post_create
            mock_get_details.assert_called_once_with(mock_story_ids[:10])

    async def test_fetch_posts_unavailable(self, provider):
        """Тест получения постов при недоступном API."""
        with patch.object(provider, "is_available", return_value=False):
            result = await provider.fetch_posts()
            assert result == []

    async def test_fetch_posts_empty_story_ids(self, provider):
        """Тест получения постов при пустом списке ID."""
        with (
            patch.object(provider, "is_available", return_value=True),
            patch.object(provider, "_get_top_story_ids", return_value=[]),
        ):
            result = await provider.fetch_posts()
            assert result == []

    @respx.mock
    async def test_get_single_post_success(self, provider, mock_story_data):
        """Тест успешного получения одного поста."""
        respx.get(f"{provider.base_url}/item/123456.json").mock(
            return_value=Response(200, json=mock_story_data)
        )

        result = await provider._get_single_post(123456)

        assert result is not None
        assert result.title == "Test Post Title"

    async def test_get_single_post_http_error(self, provider):
        """Тест получения поста при HTTP ошибке."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
                "HTTP Error"
            )

            result = await provider._get_single_post(123456)
            assert result is None
