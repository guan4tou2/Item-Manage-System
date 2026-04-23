from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_items: int
    total_quantity: int
    total_categories: int
    total_locations: int
    total_tags: int
    total_warehouses: int = 0
    low_stock_items: int = 0
    active_loans: int = 0


class CategoryBucket(BaseModel):
    category_id: int | None
    name: str | None
    count: int


class LocationBucket(BaseModel):
    location_id: int | None
    label: str | None
    count: int


class TagBucket(BaseModel):
    tag_id: int
    name: str
    count: int


class WarehouseBucket(BaseModel):
    warehouse_id: int | None
    name: str | None
    count: int


class LowStockItem(BaseModel):
    item_id: UUID
    name: str
    quantity: int
    min_quantity: int
    deficit: int  # min_quantity - quantity, always >= 1 when surfaced


class ActiveLoan(BaseModel):
    loan_id: UUID
    item_id: UUID
    item_name: str
    borrower_label: str | None
    lent_at: datetime
    expected_return: date | None
    is_overdue: bool


class TrendPoint(BaseModel):
    day: date
    count: int


class ActivityEntry(BaseModel):
    kind: str  # "quantity" | "loan_out" | "loan_return" | "item_version"
    at: datetime
    item_id: UUID | None = None
    item_name: str | None = None
    summary: str
