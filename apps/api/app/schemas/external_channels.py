from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.url_guard import URL_NOT_ALLOWED_MESSAGE, validate_webhook_url


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
    endpoint: str = Field(min_length=1, max_length=2000)
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=200)

    @field_validator("endpoint")
    @classmethod
    def _check_endpoint(cls, v: str) -> str:
        # Phase 44：endpoint 由瀏覽器的 push service 產生，一律是公網 https；
        # 伺服器之後會對它發請求，寫入時先擋掉內網／非 https（防 SSRF）。
        if not v.lower().startswith("https://"):
            raise ValueError(URL_NOT_ALLOWED_MESSAGE)
        return validate_webhook_url(v)


class WebPushSubscriptionRead(BaseModel):
    id: UUID
    endpoint: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VapidPublicKey(BaseModel):
    public_key: str
