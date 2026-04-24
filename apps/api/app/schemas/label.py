from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ItemLabel(BaseModel):
    item_id: UUID
    name: str
    quantity: int
    deep_link: str
