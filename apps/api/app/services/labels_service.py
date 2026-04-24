from __future__ import annotations

import io
from uuid import UUID

import qrcode
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories import items_repository


async def _get_owned_item(session: AsyncSession, owner_id: UUID, item_id: UUID):
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None or item.is_deleted:
        raise HTTPException(status_code=404, detail="item not found")
    return item


def _deep_link_for(item_id: UUID) -> str:
    base = get_settings().public_web_url.rstrip("/")
    return f"{base}/items/{item_id}"


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
    }
