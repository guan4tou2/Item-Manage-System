from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ReportBucket(BaseModel):
    """熱門分類／位置的一列；`label=null` 代表未分類／未指定。"""

    label: str | None
    count: int


class ReportTotals(BaseModel):
    item_count: int
    quantity: int


class ReportActivity(BaseModel):
    items_created: int
    items_deleted: int
    quantity_in: int
    quantity_out: int
    loans_out: int
    loans_returned: int
    loans_overdue: int


class ReportExpiry(BaseModel):
    expiring_soon: int
    expired: int


class ReportValuation(BaseModel):
    """估值以字串輸出（Decimal 2 位），幣別取使用者偏好。"""

    start: str
    end: str
    delta: str
    unpriced_items: int


class ReportPayload(BaseModel):
    """月報快照（version=1）；站內詳情與 Email 共用同一份 payload。"""

    version: int
    period: str
    timezone: str
    period_start: date
    period_end: date
    generated_at: datetime
    currency: str
    totals: ReportTotals
    activity: ReportActivity
    expiry: ReportExpiry
    valuation: ReportValuation
    top_categories: list[ReportBucket]
    top_locations: list[ReportBucket]
    has_activity: bool


class ReportRead(BaseModel):
    id: UUID
    period: str
    generated_at: datetime
    payload: ReportPayload


class ReportListResponse(BaseModel):
    items: list[ReportRead]
    total: int
    limit: int
    offset: int
