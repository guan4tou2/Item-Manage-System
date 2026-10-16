from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    parent_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=50)
    kind: Optional[str] = Field(default=None, max_length=20)
    sort_order: int = Field(default=0, ge=0)
    floor_plan_image_id: Optional[UUID] = None


class LocationUpdate(BaseModel):
    parent_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    kind: Optional[str] = Field(default=None, max_length=20)
    sort_order: Optional[int] = Field(default=None, ge=0)
    floor_plan_image_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")


class LocationRead(BaseModel):
    id: int
    parent_id: Optional[int] = None
    name: str
    kind: Optional[str] = None
    sort_order: int = 0
    floor_plan_image_id: Optional[UUID] = None
    path: str


class LocationTreeNode(LocationRead):
    item_count: int = 0
    children: list["LocationTreeNode"] = Field(default_factory=list)


class LocationPathNode(BaseModel):
    id: int
    name: str
    kind: Optional[str] = None


class LocationPath(BaseModel):
    id: int
    path: str
    nodes: list[LocationPathNode]


class LocationReorder(BaseModel):
    parent_id: Optional[int] = None
    location_ids: list[int] = Field(min_length=1)


LocationTreeNode.model_rebuild()
