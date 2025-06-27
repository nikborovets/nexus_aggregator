"""Pydantic схемы для постов."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class PostBase(BaseModel):
    """Базовая схема поста."""

    title: str
    url: HttpUrl
    source: str


class PostCreate(PostBase):
    """Схема для создания поста."""

    published_at: datetime


class PostResponse(PostBase):
    """Схема для возврата поста через API."""

    id: int
    published_at: datetime

    model_config = {"from_attributes": True}


class PostFilter(BaseModel):
    """Схема для фильтрации постов."""

    source: str | None = None
    search: str | None = None


class PostListResponse(BaseModel):
    """Схема для списка постов с метаданными пагинации."""

    posts: list[PostResponse]
    total: int
    page: int
    size: int
    pages: int


class SourceStats(BaseModel):
    """Схема для статистики по источнику."""

    source: str
    total_posts: int
