from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import CategoryRead
from app.schemas.location import LocationRead
from app.schemas.tag import TagRead


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    quantity: int = Field(default=1, ge=0)
    min_quantity: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    image_id: Optional[UUID] = None
    tag_names: list[str] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    min_quantity: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    image_id: Optional[UUID] = None
    tag_names: Optional[list[str]] = None

    model_config = ConfigDict(extra="forbid")


class ItemBulkUpdate(BaseModel):
    item_ids: list[UUID] = Field(min_length=1, max_length=100)
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    tag_names: Optional[list[str]] = None
    tag_mode: Literal["replace", "append"] = "replace"

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_update_field(self) -> "ItemBulkUpdate":
        if not ({"category_id", "location_id", "tag_names"} & self.model_fields_set):
            raise ValueError("at least one bulk update field is required")
        return self


class ItemBulkDelete(BaseModel):
    item_ids: list[UUID] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid")


class ItemBulkResult(BaseModel):
    updated: int = 0
    deleted: int = 0


class ItemRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    quantity: int
    min_quantity: Optional[int]
    notes: Optional[str]
    is_favorite: bool
    image_id: Optional[UUID]
    warehouse_id: Optional[int]
    owner_id: UUID
    owner_username: str
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
