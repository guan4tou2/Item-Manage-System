from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai import (
    AiSuggestResponse,
    HistorySuggestions,
    ReceiptItemSnapshot,
    ReceiptSnapshot,
)
from app.schemas.item import ItemRead

DraftStatus = Literal[
    "pending", "processing", "ready", "failed", "accepted", "discarded"
]
DraftSource = Literal["batch_photo", "receipt"]
DraftErrorCode = Literal[
    "ai_disabled", "quota_exhausted", "upstream_error", "image_missing"
]


class DraftPayload(BaseModel):
    """草稿建議快照（version=1）。全欄位必填。"""

    version: int
    ai: Optional[AiSuggestResponse]
    history: HistorySuggestions
    receipt: Optional[ReceiptSnapshot] = None
    receipt_item: Optional[ReceiptItemSnapshot] = None


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_ids: list[UUID] = Field(min_length=1, max_length=10)


class ReceiptReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verified_at: datetime
    note: Optional[str] = None


class ReceiptReviewWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: Optional[str] = Field(default=None, max_length=200)


class ReceiptLineRead(BaseModel):
    draft_id: UUID
    index: int
    name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None
    status: DraftStatus
    item_id: Optional[UUID] = None


class ReceiptRead(BaseModel):
    receipt_id: UUID
    snapshot: Optional[ReceiptSnapshot] = None
    review: Optional[ReceiptReviewRead] = None
    image_id: Optional[UUID] = None
    lines: list[ReceiptLineRead]


class DraftRead(BaseModel):
    id: UUID
    source: DraftSource
    status: DraftStatus
    image_id: Optional[UUID]
    item_id: Optional[UUID]
    error_code: Optional[DraftErrorCode]
    payload: DraftPayload
    processed_at: Optional[datetime]
    created_at: datetime
    receipt_id: Optional[UUID] = None
    receipt_review: Optional[ReceiptReviewRead] = None


class DraftCreateResponse(BaseModel):
    created: list[DraftRead]
    skipped_image_ids: list[UUID]


class DraftCounts(BaseModel):
    pending: int
    processing: int
    ready: int
    failed: int
    accepted: int
    discarded: int


class DraftListResponse(BaseModel):
    items: list[DraftRead]
    total: int
    counts: DraftCounts


class DraftAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: int = Field(default=1, ge=0)
    cost: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    tag_names: list[str] = Field(default_factory=list)


class DraftAcceptResponse(BaseModel):
    draft: DraftRead
    item: ItemRead


class DraftDiscardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[UUID] = Field(min_length=1, max_length=50)


class DraftDiscardSkipped(BaseModel):
    id: UUID
    reason: str


class DraftDiscardResponse(BaseModel):
    discarded: int
    skipped: list[DraftDiscardSkipped]


class ReceiptCreateResponse(BaseModel):
    """`POST /api/ai/receipts` 回應（Phase 33）。"""

    receipt_id: UUID
    truncated: bool
    created: list[DraftRead]
