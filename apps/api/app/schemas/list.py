from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ListKind = Literal["travel", "shopping", "collection", "generic"]


class ListCreate(BaseModel):
    kind: ListKind
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(default=None, ge=0)


class ListUpdate(BaseModel):
    kind: Optional[ListKind] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class ListEntryRead(BaseModel):
    id: UUID
    list_id: UUID
    position: int
    name: str
    quantity: Optional[int]
    note: Optional[str]
    price: Optional[Decimal]
    link: Optional[str]
    is_done: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListEntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    position: Optional[int] = Field(default=None, ge=0)
    quantity: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    link: Optional[str] = Field(default=None, max_length=500)
    is_done: bool = False


class ListEntryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(default=None, ge=1)
    note: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    link: Optional[str] = Field(default=None, max_length=500)
    is_done: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class ListSummary(BaseModel):
    id: UUID
    kind: str
    title: str
    description: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    budget: Optional[Decimal]
    entry_count: int
    done_count: int
    created_at: datetime
    updated_at: datetime


class ListRead(ListSummary):
    pass


class ListDetail(ListSummary):
    entries: list[ListEntryRead]


class ListListResponse(BaseModel):
    items: list[ListSummary]
    total: int


class ReorderRequest(BaseModel):
    entry_ids: list[UUID]
