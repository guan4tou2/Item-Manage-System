from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.label import ItemLabel, LocationLabel
from app.services import label_pdf_service, labels_service

router = APIRouter(prefix="/api/items", tags=["labels"])

#: Phase 36：位置標籤（貼在櫃子／箱子；掃碼 → 該位置物品清單）
location_router = APIRouter(prefix="/api/locations", tags=["labels"])


@router.get(
    "/labels.pdf",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}},
        404: {"description": "Item not found"},
    },
)
async def item_labels_pdf(
    ids: Annotated[list[UUID], Query(min_length=1, max_length=100)],
    start: Annotated[int, Query(ge=0, le=20)] = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Phase 41：A4 物品標籤 PDF（3×7、QR＋Code128；`start` 跳過前 N 格）。"""
    labels = await labels_service.get_item_labels_bulk(session, user.id, ids)
    pdf = label_pdf_service.render_item_labels_pdf(labels, start=start)
    filename = f"item-labels-{datetime.now(timezone.utc):%Y%m%d}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


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


@location_router.get(
    "/{location_id}/qr.png",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Location not found"},
    },
)
async def location_qr_png(
    location_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """位置 QR（Phase 36）：內容為該位置（含子孫）的物品清單深連結。"""
    png = await labels_service.get_location_qr_png(session, user.id, location_id)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=60"},
    )


@location_router.get("/{location_id}/label", response_model=LocationLabel)
async def location_label(
    location_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LocationLabel:
    """位置標籤資料（Phase 36）：名稱／完整路徑／含子孫物品數／深連結。"""
    data = await labels_service.get_location_label(session, user.id, location_id)
    return LocationLabel.model_validate(data)
