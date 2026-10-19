from __future__ import annotations
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AiSuggestRequest(BaseModel):
    image_id: UUID
    hint: Optional[str] = Field(default=None, max_length=200)


class AiSuggestResponse(BaseModel):
    name: str
    description: Optional[str] = None
    category_suggestion: Optional[str] = None
    tag_suggestions: list[str] = Field(default_factory=list)


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
    """歷史規則建議（草稿 payload.history 與 suggest-classification 共用形狀）。"""

    category: Optional[BucketSuggestion]
    location: Optional[BucketSuggestion]
    tags: list[TagSuggestion]


class ClassificationSuggestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


# --- Phase 33：收據抽取 ------------------------------------------------------


class ReceiptItem(BaseModel):
    """收據上的單一品項（金額已由伺服器補齊）。"""

    name: str
    quantity: int
    unit_price: Optional[Decimal]
    subtotal: Optional[Decimal]


class ReceiptExtraction(BaseModel):
    """LLM 抽取結果（尚未落地成草稿）。"""

    merchant: Optional[str]
    purchased_at: Optional[str]
    currency: Optional[str]
    total: Optional[Decimal]
    items: list[ReceiptItem]


class ReceiptCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_ids: list[UUID] = Field(min_length=1, max_length=10)


class ReceiptSnapshot(BaseModel):
    """收據中繼資料快照（存於每個品項草稿的 payload）。"""

    merchant: Optional[str]
    purchased_at: Optional[str]
    currency: Optional[str]
    total: Optional[Decimal]
    item_total: Optional[Decimal]
    discrepancy: Optional[Decimal]
    page_count: int
    truncated: bool


class ReceiptItemSnapshot(BaseModel):
    """品項在收據上的位置與金額（存於該品項草稿的 payload）。"""

    index: int
    quantity: int
    unit_price: Optional[Decimal]
    subtotal: Optional[Decimal]
