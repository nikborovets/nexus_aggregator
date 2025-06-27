"""API роутер для постов."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from nexus.core.db import get_async_session
from nexus.posts.schemas import PostFilter, PostListResponse, PostResponse
from nexus.posts.service import PostService

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)


@router.get("/", response_model=PostListResponse)
async def get_posts(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    source: str = Query(None, description="Фильтр по источнику"),
    search: str = Query(None, description="Поиск по заголовку и URL"),
    session: AsyncSession = Depends(get_async_session),
) -> PostListResponse:
    """Получить список постов с пагинацией и фильтрацией."""
    post_service = PostService(session)
    
    # Создаем фильтр
    filters = PostFilter(source=source, search=search) if (source or search) else None
    
    # Получаем посты
    posts, total = await post_service.get_posts(
        page=page,
        size=size,
        filters=filters,
    )
    
    return PostListResponse(
        posts=posts,
        total=total,
        page=page,
        size=len(posts),
        pages=(total + size - 1) // size,  # Вычисляем общее количество страниц
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> PostResponse:
    """Получить пост по ID."""
    post_service = PostService(session)
    
    post = await post_service.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    return post


@router.get("/sources/{source_name}", response_model=List[PostResponse])
async def get_posts_by_source(
    source_name: str,
    limit: int = Query(50, ge=1, le=100, description="Максимальное количество постов"),
    session: AsyncSession = Depends(get_async_session),
) -> List[PostResponse]:
    """Получить посты по источнику."""
    post_service = PostService(session)
    
    posts = await post_service.get_posts_by_source(source_name, limit=limit)
    
    return posts


@router.get("/stats/sources")
async def get_source_stats(
    session: AsyncSession = Depends(get_async_session),
):
    """Получить статистику по источникам."""
    post_service = PostService(session)
    
    stats = await post_service.get_source_stats()
    
    return {"sources": stats} 