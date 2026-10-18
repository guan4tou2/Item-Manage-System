from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

#: Stored membership roles. `owner` is never stored — it is derived from
#: `groups.owner_id` (single source of truth, checked before the role).
MemberRole = Literal["admin", "editor", "viewer"]
#: Effective role of a member: the stored role, or `owner` for the group owner.
EffectiveRole = Literal["owner", "admin", "editor", "viewer"]


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    model_config = ConfigDict(extra="forbid")


class GroupMemberRead(BaseModel):
    user_id: UUID
    username: str
    joined_at: datetime
    role: EffectiveRole


class GroupSummary(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    owner_username: str
    is_owner: bool
    member_count: int
    created_at: datetime
    updated_at: datetime
    my_role: EffectiveRole


class GroupDetail(GroupSummary):
    members: list[GroupMemberRead]


class GroupAddMember(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    role: MemberRole = "editor"


class GroupMemberRoleUpdate(BaseModel):
    role: MemberRole
    model_config = ConfigDict(extra="forbid")
