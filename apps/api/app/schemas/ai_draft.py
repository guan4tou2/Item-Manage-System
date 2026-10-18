from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai import AiSuggestResponse
from app.schemas.item import ItemRead

DraftStatus = Literal[
    "pending", "processing", "ready", "failed", "accepted", "discarded"
]
DraftSource = Literal["batch_photo", "receipt"]
DraftErrorCode = Literal[
    "ai_disabled", "quota_exhausted", "upstream_error", "image_missing"
]


class BucketSuggestion(BaseModel):
    """歷史規則建議（分類／位置）。全欄位必填。"""

    id: int
    name: str
    item_count: int
    score: int


class TagSuggestion(BaseModel):
    name: str
    item_count: int
    score: int


class HistorySuggestions(BaseModel):
    """歷史規則建議（payload.history 與 suggest-classification 的共用形狀）。"""

    category: Optional[BucketSuggestion]
    location: Optional[BucketSuggestion]
    tags: list[TagSuggestion]


class DraftPayload(BaseModel):
    """草稿建議快照（version=1）。全欄位必填。"""

    version: int
    ai: Optional[AiSuggestResponse]
    history: HistorySuggestions


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_ids: list[UUID] = Field(min_length=1, max_length=10)


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
