from __future__ import annotations

from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_items: int
    total_quantity: int
    total_categories: int
    total_locations: int
    total_tags: int


class CategoryBucket(BaseModel):
    category_id: int | None
    name: str | None
    count: int


class LocationBucket(BaseModel):
    location_id: int | None
    label: str | None
    count: int


class TagBucket(BaseModel):
    tag_id: int
    name: str
    count: int
