from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class BarcodeLocalMatch(BaseModel):
    id: UUID
    name: str
    quantity: int
    image_id: Optional[UUID] = None
    location_path: Optional[str] = None


class BarcodeExternal(BaseModel):
    source: str
    name: str
    description: str
    image_url: Optional[str] = None
    suggested_category_id: Optional[int] = None


class BarcodeLookupResponse(BaseModel):
    code: str
    local_matches: list[BarcodeLocalMatch]
    external: Optional[BarcodeExternal] = None
    external_status: str
    cached: bool = False
