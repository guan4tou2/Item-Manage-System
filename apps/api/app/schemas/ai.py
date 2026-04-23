from __future__ import annotations
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AiSuggestRequest(BaseModel):
    image_id: UUID
    hint: Optional[str] = Field(default=None, max_length=200)


class AiSuggestResponse(BaseModel):
    name: str
    description: Optional[str] = None
    category_suggestion: Optional[str] = None
    tag_suggestions: list[str] = Field(default_factory=list)
