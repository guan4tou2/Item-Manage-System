from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TagRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class TagReadWithCount(BaseModel):
    id: int
    name: str
    item_count: int

    model_config = ConfigDict(from_attributes=True)


class TagRename(BaseModel):
    name: str = Field(min_length=1, max_length=50)

    model_config = ConfigDict(extra="forbid")


class TagMerge(BaseModel):
    target_id: int

    model_config = ConfigDict(extra="forbid")


class TagMergeResult(BaseModel):
    target_id: int
    reassigned_item_count: int


class PruneOrphansResult(BaseModel):
    deleted_count: int
