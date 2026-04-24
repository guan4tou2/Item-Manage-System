from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1)
    secret: Optional[str] = Field(default=None, max_length=200)
    events: list[str] = Field(default_factory=list)


class WebhookUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    url: Optional[str] = None
    secret: Optional[str] = Field(default=None, max_length=200)
    events: Optional[list[str]] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class WebhookRead(BaseModel):
    id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime
    last_fired_at: Optional[datetime]
    last_status: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class WebhookDeliveryRead(BaseModel):
    id: UUID
    webhook_id: UUID
    event: str
    payload: dict[str, Any]
    status_code: Optional[int]
    response_excerpt: Optional[str]
    attempt: int
    next_retry_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessRetriesResult(BaseModel):
    processed: int  # deliveries we tried to re-send in this call
    succeeded: int  # of those, how many got a 2xx response
    remaining: int  # how many still have next_retry_at set after this run
