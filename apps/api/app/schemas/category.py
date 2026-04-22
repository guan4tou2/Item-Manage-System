from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    parent_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class CategoryRead(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeNode(CategoryRead):
    children: list["CategoryTreeNode"] = []


CategoryTreeNode.model_rebuild()
