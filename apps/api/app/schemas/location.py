from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanRegion(BaseModel):
    """相對父位置平面圖的正規化矩形。"""

    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0, le=1, strict=True, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, strict=True, allow_inf_nan=False)
    w: float = Field(ge=0.02, le=1, strict=True, allow_inf_nan=False)
    h: float = Field(ge=0.02, le=1, strict=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_bounds(self) -> PlanRegion:
        if self.x + self.w > 1 + 1e-12 or self.y + self.h > 1 + 1e-12:
            raise ValueError("區域不可超出圖片邊界")
        for key in ("x", "y", "w", "h"):
            setattr(self, key, round(getattr(self, key), 4))
        # 獨立四捨五入可能讓右／下邊界多出 0.0001，向圖片內夾限。
        self.w = min(self.w, round(1 - self.x, 4))
        self.h = min(self.h, round(1 - self.y, 4))
        return self


class LocationCreate(BaseModel):
    parent_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=50)
    kind: Optional[str] = Field(default=None, max_length=20)
    sort_order: int = Field(default=0, ge=0)
    floor_plan_image_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")


class LocationUpdate(BaseModel):
    plan_region: Optional[PlanRegion] = None
    parent_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    kind: Optional[str] = Field(default=None, max_length=20)
    sort_order: Optional[int] = Field(default=None, ge=0)
    floor_plan_image_id: Optional[UUID] = None

    model_config = ConfigDict(extra="forbid")


class LocationRead(BaseModel):
    plan_region: Optional[PlanRegion] = None
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
