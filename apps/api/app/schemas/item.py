from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead
from app.schemas.location import LocationRead
from app.schemas.tag import TagRead


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: int = Field(default=1, ge=0)
    notes: Optional[str] = None
    tag_names: list[str] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    tag_names: Optional[list[str]] = None

    model_config = ConfigDict(extra="forbid")


class ItemRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    quantity: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead]
    location: Optional[LocationRead]
    tags: list[TagRead]

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    items: list[ItemRead]
    total: int
    page: int
    per_page: int
