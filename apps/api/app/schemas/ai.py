from __future__ import annotations
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
