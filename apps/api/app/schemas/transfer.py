from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


TransferStatus = Literal["pending", "accepted", "rejected", "cancelled"]


class TransferCreate(BaseModel):
    item_id: UUID
    to_username: str = Field(min_length=1, max_length=50)
    message: Optional[str] = None


class TransferRead(BaseModel):
    id: UUID
    item_id: UUID
    item_name: str
    from_user_id: UUID
    from_username: str
    to_user_id: UUID
    to_username: str
    status: TransferStatus
    message: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
