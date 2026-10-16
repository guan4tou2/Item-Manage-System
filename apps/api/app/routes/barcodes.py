from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.item import Item
from app.models.user import User
from app.repositories import items_repository
from app.schemas.barcode import (
    BarcodeExternal,
    BarcodeLocalMatch,
    BarcodeLookupResponse,
)
from app.services import barcode_service

router = APIRouter(prefix="/api/barcodes", tags=["barcodes"])

MAX_CODE_LENGTH = 64


def _location_path(item: Item) -> str | None:
    if item.location is None:
        return None
    parts = [item.location.floor, item.location.room, item.location.zone]
    return " / ".join(part for part in parts if part) or None


@router.get("/{code}", response_model=BarcodeLookupResponse)
async def lookup_barcode(
    code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BarcodeLookupResponse:
    """內查（owner 範圍、canonical 精確比對）；無命中才外查（含快取）。"""
    canonical = barcode_service.canonicalize(code)
    if not canonical or len(canonical) > MAX_CODE_LENGTH:
        raise HTTPException(status_code=422, detail="invalid barcode")

    items = await items_repository.list_by_barcode(session, user.id, canonical)
    matches = [
        BarcodeLocalMatch(
            id=item.id,
            name=item.name,
            quantity=item.quantity,
            image_id=item.image_id,
            location_path=_location_path(item),
        )
        for item in items
    ]
    if matches:
        return BarcodeLookupResponse(
            code=canonical,
            local_matches=matches,
            external=None,
            external_status="skipped",
        )

    lookup = await barcode_service.lookup_external(session, canonical)
    external = None
    if lookup.status == barcode_service.STATUS_OK and lookup.external:
        suggested = await barcode_service.suggest_category_id(
            session, user.id, lookup.categories_text
        )
        external = BarcodeExternal(
            source=lookup.source,
            name=str(lookup.external.get("name") or ""),
            description=str(lookup.external.get("description") or ""),
            image_url=lookup.external.get("image_url"),
            suggested_category_id=suggested,
        )
    return BarcodeLookupResponse(
        code=canonical,
        local_matches=[],
        external=external,
        external_status=lookup.status,
        cached=lookup.cached,
    )
