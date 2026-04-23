from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    model_config = ConfigDict(extra="forbid")


class GroupMemberRead(BaseModel):
    user_id: UUID
    username: str
    joined_at: datetime


class GroupSummary(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    owner_username: str
    is_owner: bool
    member_count: int
    created_at: datetime
    updated_at: datetime


class GroupDetail(GroupSummary):
    members: list[GroupMemberRead]


class GroupAddMember(BaseModel):
    username: str = Field(min_length=1, max_length=50)
