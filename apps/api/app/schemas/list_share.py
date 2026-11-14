"""分享管理與公開資料的獨立白名單。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.list import ListKind


class ListShareCreate(BaseModel):
    expires_in_days: Literal[1, 7, 30] | None
    show_prices: bool = False
    model_config = ConfigDict(extra="forbid")


class ListShareRead(BaseModel):
    id: UUID
    token_prefix: str
    show_prices: bool
    expires_at: datetime | None
    created_at: datetime
    last_accessed_at: datetime | None
    access_count: int
    model_config = ConfigDict(from_attributes=True)


class ListShareCreated(ListShareRead):
    token: str


class PublicListEntry(BaseModel):
    name: str
    quantity: int | None
    note: str | None
    link: str | None
    is_done: bool
    price: Decimal | None = None


class PublicList(BaseModel):
    kind: ListKind
    title: str
    description: str | None
    start_date: date | None
    end_date: date | None
    entries: list[PublicListEntry]
    budget: Decimal | None = None
    currency: str | None = None
