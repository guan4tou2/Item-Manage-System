from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportBucket(BaseModel):
    """熱門分類／位置的一列；`label=null` 代表未分類／未指定。"""

    label: str | None = None
    count: int = 0


class ReportTotals(BaseModel):
    item_count: int = 0
    quantity: int = 0


class ReportActivity(BaseModel):
    items_created: int = 0
    items_deleted: int = 0
    quantity_in: int = 0
    quantity_out: int = 0
    loans_out: int = 0
    loans_returned: int = 0
    loans_overdue: int = 0


class ReportExpiry(BaseModel):
    expiring_soon: int = 0
    expired: int = 0


class ReportValuation(BaseModel):
    """估值以字串輸出（Decimal 2 位），幣別取使用者偏好。"""

    start: str = "0.00"
    end: str = "0.00"
    delta: str = "0.00"
    unpriced_items: int = 0


class ReportPayload(BaseModel):
    """月報快照（version=1）；站內詳情與 Email 共用同一份 payload。"""

    version: int = 1
    period: str
    timezone: str = "Asia/Taipei"
    period_start: date
    period_end: date
    generated_at: datetime
    currency: str = "TWD"
    totals: ReportTotals = Field(default_factory=ReportTotals)
    activity: ReportActivity = Field(default_factory=ReportActivity)
    expiry: ReportExpiry = Field(default_factory=ReportExpiry)
    valuation: ReportValuation = Field(default_factory=ReportValuation)
    top_categories: list[ReportBucket] = Field(default_factory=list)
    top_locations: list[ReportBucket] = Field(default_factory=list)
    has_activity: bool = False


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
