from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app import clock
from app.schemas.item import COST_FIELD


class BatchCreate(BaseModel):
    #: 省略＝首建時沿用 items.quantity（既有數量併入第一批）
    quantity: Optional[int] = Field(default=None, ge=1)
    expiry_date: Optional[date] = None
    received_at: Optional[date] = None
    note: Optional[str] = None
    unit_cost: Optional[Decimal] = COST_FIELD


class BatchUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, ge=1)
    expiry_date: Optional[date] = None
    note: Optional[str] = None
    unit_cost: Optional[Decimal] = COST_FIELD

    model_config = ConfigDict(extra="forbid")


class BatchConsume(BaseModel):
    quantity: int = Field(ge=1)


class BatchConsumeSplit(BaseModel):
    batch_id: UUID
    quantity: int


class BatchConsumeResult(BaseModel):
    consumed: list[BatchConsumeSplit]


class BatchRead(BaseModel):
    id: UUID
    item_id: UUID
    quantity: int
    expiry_date: Optional[date]
    received_at: Optional[date]
    note: Optional[str]
    unit_cost: Optional[Decimal] = None
    is_depleted: bool
    days_left: Optional[int]
    status: Literal["ok", "expiring", "expired"]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_batch(cls, batch, *, today: date | None = None) -> "BatchRead":
        return cls(
            id=batch.id,
            item_id=batch.item_id,
            quantity=batch.quantity,
            expiry_date=batch.expiry_date,
            received_at=batch.received_at,
            note=batch.note,
            unit_cost=batch.unit_cost,
            is_depleted=batch.is_depleted,
            days_left=(
                None
                if batch.expiry_date is None
                else clock.days_left(batch.expiry_date, today=today)
            ),
            status=clock.expiry_status(batch.expiry_date, today=today),
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )
