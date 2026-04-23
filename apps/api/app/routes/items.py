from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.item import ItemCreate, ItemListResponse, ItemRead, ItemUpdate
from app.services import items_service

router = APIRouter(prefix="/api/items", tags=["items"])


@router.get("", response_model=ItemListResponse)
async def list_items(
    q: str | None = None,
    category_id: int | None = None,
    location_id: int | None = None,
    tag_ids: list[int] | None = Query(default=None),
    favorite: bool | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemListResponse:
    return await items_service.list_items(
        session,
        user.id,
        q=q,
        category_id=category_id,
        location_id=location_id,
        tag_ids=tag_ids,
        favorite=favorite,
        page=page,
        per_page=per_page,
    )


@router.post("/{item_id}/favorite", response_model=ItemRead)
async def toggle_favorite(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemRead:
    return await items_service.toggle_favorite(session, user.id, item_id)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ItemCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemRead:
    return await items_service.create_item(session, user.id, body)


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemRead:
    return await items_service.get_item(session, user.id, item_id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: UUID,
    body: ItemUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemRead:
    return await items_service.update_item(session, user.id, item_id, body)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_item(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await items_service.delete_item(session, user.id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
