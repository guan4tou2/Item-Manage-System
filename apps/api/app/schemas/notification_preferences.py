from __future__ import annotations

from pydantic import BaseModel, Field


class NotificationPreferenceType(BaseModel):
    key: str
    group: str
    locked: bool


class NotificationPreferenceUpdate(BaseModel):
    type: str
    channel: str
    enabled: bool


class NotificationPreferencesUpdateRequest(BaseModel):
    updates: list[NotificationPreferenceUpdate] = Field(default_factory=list)


class NotificationPreferencesResponse(BaseModel):
    types: list[NotificationPreferenceType]
    channels: list[str]
    matrix: dict[str, dict[str, bool]]
    has_custom: bool
    channel_availability: dict[str, bool]
