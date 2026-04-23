from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


StocktakeStatus = Literal["open", "completed", "cancelled"]


class StocktakeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class StocktakeItemRead(BaseModel):
    id: int
    item_id: UUID
    expected_quantity: int
    actual_quantity: int
    note: Optional[str]
    scanned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StocktakeRead(BaseModel):
    id: UUID
    name: str
    status: StocktakeStatus
    started_at: datetime
    completed_at: Optional[datetime]
    item_count: int = 0
    discrepancy_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StocktakeDetail(StocktakeRead):
    items: list[StocktakeItemRead]


class StocktakeItemScan(BaseModel):
    item_id: UUID
    actual_quantity: int = Field(ge=0)
    note: Optional[str] = None
