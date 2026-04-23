from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


FieldType = Literal["text", "number", "date", "bool"]


# item_types
class ItemTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=50)


class ItemTypeRead(BaseModel):
    id: int
    name: str
    icon: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# custom_fields
class CustomFieldCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    field_type: FieldType


class CustomFieldRead(BaseModel):
    id: int
    name: str
    field_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemCustomValueSet(BaseModel):
    custom_field_id: int
    value: Optional[Any]


class ItemCustomValueRead(BaseModel):
    custom_field_id: int
    value: Optional[Any]

    model_config = ConfigDict(from_attributes=True)


# templates
class ItemTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]


class ItemTemplateRead(BaseModel):
    id: int
    name: str
    payload: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# history
class QuantityLogRead(BaseModel):
    id: UUID
    item_id: UUID
    user_id: Optional[UUID]
    old_quantity: int
    new_quantity: int
    reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemVersionRead(BaseModel):
    id: UUID
    item_id: UUID
    user_id: Optional[UUID]
    snapshot: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
