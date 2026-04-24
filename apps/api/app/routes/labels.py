from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.label import ItemLabel
from app.services import labels_service

router = APIRouter(prefix="/api/items", tags=["labels"])


@router.get(
    "/{item_id}/qr.png",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Item not found"},
    },
)
async def item_qr_png(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    png = await labels_service.get_item_qr_png(session, user.id, item_id)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.get("/{item_id}/label", response_model=ItemLabel)
async def item_label(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemLabel:
    data = await labels_service.get_item_label(session, user.id, item_id)
    return ItemLabel.model_validate(data)
