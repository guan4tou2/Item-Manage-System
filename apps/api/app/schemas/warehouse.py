from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class WarehouseRead(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)
