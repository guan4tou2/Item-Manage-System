"""AI 自然語言搜尋與物品問答（Phase 34）的 API schema。"""
from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.item import ItemRead

SearchFallbackReason = Literal[
    "ai_disabled", "quota_exhausted", "upstream_error", "unparsed"
]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=300)

    @field_validator("query")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("query must not be blank")
        return text


class AppliedBucket(BaseModel):
    id: int
    name: str
    path: Optional[str] = None


class AppliedFilters(BaseModel):
    """實際套用的條件（前端「理解為」chip）。全欄位必填可為 null。"""

    q: Optional[str]
    category: Optional[AppliedBucket]
    location: Optional[AppliedBucket]
    tags: list[AppliedBucket]
    expiry: Optional[str]
    loan: Optional[str]
    favorite: Optional[bool]
    min_quantity: Optional[int]
    max_quantity: Optional[int]
    sort: Optional[str]


class SearchResponse(BaseModel):
    filters: dict
    applied: AppliedFilters
    unresolved: list[str]
    items: list[ItemRead]
    total: int
    fallback_reason: Optional[SearchFallbackReason]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=300)
    item_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("question must not be blank")
        return text


class Citation(BaseModel):
    item_id: UUID
    name: str
    path: Optional[str]


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    grounded: bool
