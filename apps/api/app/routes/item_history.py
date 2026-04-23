from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories import items_repository
from app.schemas.customization import ItemVersionRead, QuantityLogRead
from app.services import item_history_service
from app.services.visibility_service import visible_item_owner_ids

router = APIRouter(prefix="/api/items/{item_id}", tags=["item-history"])


async def _ensure_visible(session: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    visible = await visible_item_owner_ids(session, user_id)
    item = await items_repository.get_visible(session, visible, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")


@router.get("/quantity-logs", response_model=list[QuantityLogRead])
async def list_quantity_logs(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _ensure_visible(session, user.id, item_id)
    rows = await item_history_service.list_quantity_logs(session, item_id)
    return [QuantityLogRead.model_validate(r) for r in rows]


@router.get("/versions", response_model=list[ItemVersionRead])
async def list_versions(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _ensure_visible(session, user.id, item_id)
    rows = await item_history_service.list_item_versions(session, item_id)
    return [ItemVersionRead.model_validate(r) for r in rows]
