from __future__ import annotations

import io
from uuid import UUID

import qrcode
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.location import Location
from app.repositories import items_repository, locations_repository


async def _get_owned_item(session: AsyncSession, owner_id: UUID, item_id: UUID):
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None or item.is_deleted:
        raise HTTPException(status_code=404, detail="item not found")
    return item


async def _get_owned_location(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> Location:
    """本人位置；他人／不存在一律 404（不洩漏存在性）。"""
    location = await locations_repository.get_owned(session, owner_id, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="location not found")
    return location


def _deep_link_for(item_id: UUID) -> str:
    base = get_settings().public_web_url.rstrip("/")
    return f"{base}/items/{item_id}"


def location_deep_link(location_id: int) -> str:
    """位置深連結（Phase 36）：導向**該位置（含子孫）的物品清單**。

    位置 id 為 int（非 UUID）→ 以 query param 承載；`location_scope` 預設 `subtree`，
    故清單天然包含子孫位置。
    """
    base = get_settings().public_web_url.rstrip("/")
    return f"{base}/items?location={location_id}"


def render_qr_png(payload: str, *, box_size: int = 8, border: int = 2) -> bytes:
    """Render a QR code encoding ``payload`` and return PNG bytes."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def get_item_qr_png(
    session: AsyncSession, owner_id: UUID, item_id: UUID
) -> bytes:
    await _get_owned_item(session, owner_id, item_id)
    return render_qr_png(_deep_link_for(item_id))


async def get_item_label(
    session: AsyncSession, owner_id: UUID, item_id: UUID
) -> dict:
    item = await _get_owned_item(session, owner_id, item_id)
    return {
        "item_id": str(item.id),
        "name": item.name,
        "quantity": int(item.quantity),
        "deep_link": _deep_link_for(item.id),
        "barcode": item.barcode,
    }


# --- Phase 36：位置 QR 標籤 -------------------------------------------------


async def get_location_qr_png(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> bytes:
    await _get_owned_location(session, owner_id, location_id)
    return render_qr_png(location_deep_link(location_id))


async def get_location_label(
    session: AsyncSession, owner_id: UUID, location_id: int
) -> dict:
    """位置標籤資料：名稱／完整路徑／**含子孫**物品數／深連結。"""
    location = await _get_owned_location(session, owner_id, location_id)

    locations = await locations_repository.fetch_all(session, owner_id)
    path = locations_repository.path_for(locations, location.id) or location.name

    # 含子孫的物品數（與清單篩選結果一致：`location_scope=subtree`）
    subtree = await locations_repository.descendant_ids(
        session, owner_id, [location.id]
    )
    item_count = await items_repository.count_items_in_locations(
        session, owner_id, sorted(subtree)
    )

    return {
        "location_id": location.id,
        "name": location.name,
        "path": path,
        "item_count": item_count,
        "deep_link": location_deep_link(location.id),
    }
