from __future__ import annotations
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AiSuggestRequest(BaseModel):
    image_id: UUID
    hint: Optional[str] = Field(default=None, max_length=200)


class AiStatusRead(BaseModel):
    """AI 執行模式與啟用狀態（Phase 35；唯讀）。"""

    model_config = ConfigDict(extra="forbid")

    #: `live` 走真實 Gemini；`stub` 走確定性 stub 供應器
    mode: Literal["live", "stub"]
    #: AI 功能（建議／收據／搜尋／問答）目前是否可用
    enabled: bool


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
    # --- Phase 38：算術驗證與旗標（純新增；舊快照缺值 → None／unknown）---
    #: 價稅前品項合計（模型讀到的 subtotal）
    subtotal: Optional[Decimal] = None
    #: 收據層級折扣
    discount: Optional[Decimal] = None
    #: 稅額
    tax: Optional[Decimal] = None
    #: 運費／服務費
    shipping: Optional[Decimal] = None
    #: 算術值（Σ品項小計 − 折扣 + 稅 + 運費）
    calculated_total: Optional[Decimal] = None
    #: 對帳狀態：balanced／discrepancy／incomplete／unknown
    balance_status: Optional[Literal["balanced", "discrepancy", "incomplete", "unknown"]] = None
    #: 缺價（無法計算金額）的品項數（舊快照缺此鍵 → 視為 0）
    missing_price_count: Optional[int] = None
    #: AI 自述讀不確定的欄位路徑（舊快照缺此鍵 → 視為空）
    uncertain_fields: Optional[list[str]] = None


class ReceiptItemSnapshot(BaseModel):
    """品項在收據上的位置與金額（存於該品項草稿的 payload）。"""

    index: int
    quantity: int
    unit_price: Optional[Decimal]
    subtotal: Optional[Decimal]
