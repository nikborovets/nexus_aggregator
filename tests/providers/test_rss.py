"""Unit-тесты для RssProvider."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nexus.providers.rss import RssProvider


@pytest.mark.unit
class TestRssProvider:
    """Тесты для RssProvider."""

    @pytest.fixture
    def provider(self):
        """Фикстура для создания RSS провайдера."""
        return RssProvider("https://example.com/rss.xml", "test-source")

    @pytest.fixture
    def provider_auto_name(self):
        """Фикстура для создания RSS провайдера с автоопределением названия."""
        return RssProvider("https://www.example.com/feed")

    @pytest.fixture
    def mock_rss_content(self):
        """Мок RSS контента."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Test Post 1</title>
                    <link>https://example.com/post1</link>
                    <pubDate>Mon, 01 Jan 2022 00:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Test Post 2</title>
                    <link>https://example.com/post2</link>
                    <pubDate>Mon, 02 Jan 2022 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""

    @pytest.fixture
    def mock_feed_entry(self):
        """Мок RSS записи."""
        entry = MagicMock()
        entry.title = "Test Post Title"
        entry.link = "https://example.com/test"
        entry.published_parsed = (2022, 1, 1, 0, 0, 0, 0, 1, 0)
        return entry

    def test_init_with_custom_name(self):
        """Тест инициализации с пользовательским названием."""
        provider = RssProvider("https://example.com/rss.xml", "custom-source")
        assert provider.source_name == "custom-source"
        assert provider.rss_url == "https://example.com/rss.xml"

    def test_init_auto_name(self, provider_auto_name):
        """Тест автоопределения названия источника."""
        assert provider_auto_name.source_name == "example.com"

    async def test_is_available_head_success(self, provider):
        """Тест успешной проверки доступности через HEAD запрос."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.head.return_value = mock_response

            result = await provider.is_available()
            assert result is True

    async def test_is_available_head_fail_get_success(self, provider):
        """Тест fallback к GET запросу при неудачном HEAD."""
        with patch("httpx.AsyncClient") as mock_client:
            # HEAD запрос неудачен
            mock_client.return_value.__aenter__.return_value.head.side_effect = Exception(
                "HEAD failed"
            )

            # GET запрос успешен
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await provider.is_available()
            assert result is True

    async def test_is_available_both_fail(self, provider):
        """Тест неуспешной проверки доступности."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.head.side_effect = Exception(
                "HEAD failed"
            )
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
                "GET failed"
            )

            result = await provider.is_available()
            assert result is False

    async def test_fetch_rss_content_success(self, provider, mock_rss_content):
        """Тест успешного получения RSS контента."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.text = mock_rss_content
            mock_response.raise_for_status = AsyncMock()

            # Создаем AsyncMock для context manager
            mock_context = AsyncMock()
            mock_context.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_context)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await provider._fetch_rss_content()
            assert result == mock_rss_content

    async def test_fetch_rss_content_failure(self, provider):
        """Тест неуспешного получения RSS контента."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
                "Network error"
            )

            result = await provider._fetch_rss_content()
            assert result is None

    def test_parse_rss_entry_success(self, provider, mock_feed_entry):
        """Тест успешного парсинга RSS записи."""
        result = provider._parse_rss_entry(mock_feed_entry)

        assert result is not None
        assert result.title == "Test Post Title"
        assert str(result.url) == "https://example.com/test"
        assert result.source == "test-source"
        assert result.published_at == datetime(2022, 1, 1, 0, 0, 0)

    def test_parse_rss_entry_missing_title(self, provider, mock_feed_entry):
        """Тест парсинга записи без заголовка."""
        delattr(mock_feed_entry, "title")

        result = provider._parse_rss_entry(mock_feed_entry)
        assert result is None

    def test_parse_rss_entry_missing_link(self, provider, mock_feed_entry):
        """Тест парсинга записи без ссылки."""
        delattr(mock_feed_entry, "link")

        result = provider._parse_rss_entry(mock_feed_entry)
        assert result is None

    def test_parse_rss_entry_empty_title(self, provider, mock_feed_entry):
        """Тест парсинга записи с пустым заголовком."""
        mock_feed_entry.title = "   "

        result = provider._parse_rss_entry(mock_feed_entry)
        assert result is None

    def test_parse_published_date_parsed_field(self, provider):
        """Тест парсинга даты из parsed поля."""
        entry = MagicMock()
        entry.published_parsed = (2022, 1, 1, 12, 30, 45, 0, 1, 0)

        result = provider._parse_published_date(entry)
        assert result == datetime(2022, 1, 1, 12, 30, 45)

    def test_parse_published_date_updated_parsed(self, provider):
        """Тест парсинга даты из updated_parsed поля."""
        entry = MagicMock()
        entry.updated_parsed = (2022, 1, 1, 12, 30, 45, 0, 1, 0)

        result = provider._parse_published_date(entry)
        assert result == datetime(2022, 1, 1, 12, 30, 45)

    def test_parse_published_date_string_field(self, provider):
        """Тест парсинга даты из строкового поля."""
        entry = MagicMock()
        entry.published = "2022-01-01T12:30:45Z"

        result = provider._parse_published_date(entry)
        assert result == datetime(2022, 1, 1, 12, 30, 45)

    def test_parse_published_date_no_date(self, provider):
        """Тест парсинга записи без даты."""
        entry = MagicMock()
        # Удаляем все поля с датой
        for attr in ["published_parsed", "updated_parsed", "published", "updated"]:
            if hasattr(entry, attr):
                delattr(entry, attr)

        result = provider._parse_published_date(entry)
        assert result is None

    async def test_fetch_posts_success(self, provider, mock_rss_content):
        """Тест успешного получения постов."""
        with (
            patch.object(provider, "is_available", return_value=True),
            patch.object(provider, "_fetch_rss_content", return_value=mock_rss_content),
            patch("feedparser.parse") as mock_parse,
        ):
            # Мокаем результат feedparser
            mock_feed = MagicMock()
            mock_entry1 = MagicMock()
            mock_entry1.title = "Post 1"
            mock_entry1.link = "https://example.com/post1"
            mock_entry1.published_parsed = (2022, 1, 1, 0, 0, 0, 0, 1, 0)

            mock_entry2 = MagicMock()
            mock_entry2.title = "Post 2"
            mock_entry2.link = "https://example.com/post2"
            mock_entry2.published_parsed = (2022, 1, 2, 0, 0, 0, 0, 1, 0)

            mock_feed.entries = [mock_entry1, mock_entry2]
            mock_parse.return_value = mock_feed

            result = await provider.fetch_posts(limit=10)

            assert len(result) == 2
            assert result[0].title == "Post 1"
            assert result[1].title == "Post 2"

    async def test_fetch_posts_unavailable(self, provider):
        """Тест получения постов при недоступном фиде."""
        with patch.object(provider, "is_available", return_value=False):
            result = await provider.fetch_posts()
            assert result == []

    async def test_fetch_posts_no_content(self, provider):
        """Тест получения постов при отсутствии контента."""
        with (
            patch.object(provider, "is_available", return_value=True),
            patch.object(provider, "_fetch_rss_content", return_value=None),
        ):
            result = await provider.fetch_posts()
            assert result == []

    async def test_fetch_posts_empty_feed(self, provider):
        """Тест получения постов из пустого фида."""
        with (
            patch.object(provider, "is_available", return_value=True),
            patch.object(provider, "_fetch_rss_content", return_value="<rss></rss>"),
            patch("feedparser.parse") as mock_parse,
        ):
            mock_feed = MagicMock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            result = await provider.fetch_posts()
            assert result == []
