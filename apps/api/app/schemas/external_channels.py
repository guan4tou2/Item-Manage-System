from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LineLinkSet(BaseModel):
    line_user_id: str = Field(min_length=1, max_length=100)


class TelegramLinkSet(BaseModel):
    chat_id: str = Field(min_length=1, max_length=100)


class ChannelStatus(BaseModel):
    email_configured: bool
    line_configured: bool
    telegram_configured: bool
    web_push_configured: bool
    user_line_linked: bool
    user_telegram_linked: bool
    user_web_push_count: int


class WebPushSubscriptionCreate(BaseModel):
    endpoint: str = Field(min_length=1)
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=200)


class WebPushSubscriptionRead(BaseModel):
    id: UUID
    endpoint: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VapidPublicKey(BaseModel):
    public_key: str
