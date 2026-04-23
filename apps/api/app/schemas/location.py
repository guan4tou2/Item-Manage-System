from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    floor: str = Field(min_length=1, max_length=50)
    room: Optional[str] = Field(default=None, max_length=50)
    zone: Optional[str] = Field(default=None, max_length=50)
    sort_order: Optional[int] = Field(default=0, ge=0)
    floor_plan_image_id: Optional[UUID] = None


class LocationUpdate(BaseModel):
    floor: Optional[str] = Field(default=None, min_length=1, max_length=50)
    room: Optional[str] = Field(default=None, max_length=50)
    zone: Optional[str] = Field(default=None, max_length=50)
    sort_order: Optional[int] = Field(default=None, ge=0)
    floor_plan_image_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")


class LocationRead(BaseModel):
    id: int
    floor: str
    room: Optional[str]
    zone: Optional[str]
    sort_order: int = 0
    floor_plan_image_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class LocationReorder(BaseModel):
    location_ids: list[int]
