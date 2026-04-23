from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import groups_repository
from app.schemas.group import (
    GroupAddMember,
    GroupCreate,
    GroupDetail,
    GroupMemberRead,
    GroupSummary,
    GroupUpdate,
)


async def _user_by_username(session: AsyncSession, username: str) -> User | None:
    return (await session.execute(
        select(User).where(User.username == username)
    )).scalar_one_or_none()


async def _summary(session: AsyncSession, g, current_user_id: UUID) -> GroupSummary:
    owner = (await session.execute(
        select(User).where(User.id == g.owner_id)
    )).scalar_one()
    count = await groups_repository.member_count(session, g.id)
    return GroupSummary(
        id=g.id, name=g.name, owner_id=g.owner_id, owner_username=owner.username,
        is_owner=(g.owner_id == current_user_id), member_count=count,
        created_at=g.created_at, updated_at=g.updated_at,
    )


async def list_groups(session: AsyncSession, user_id: UUID) -> list[GroupSummary]:
    groups = await groups_repository.list_for_user(session, user_id)
    return [await _summary(session, g, user_id) for g in groups]


async def create_group(
    session: AsyncSession, owner_id: UUID, body: GroupCreate
) -> GroupSummary:
    g = await groups_repository.create(session, owner_id=owner_id, name=body.name)
    return await _summary(session, g, owner_id)


async def _ensure_visible(session, user_id, group_id):
    g = await groups_repository.get_for_member(session, user_id, group_id)
    if g is None:
        raise HTTPException(status_code=404, detail="group not found")
    return g


async def _ensure_owned(session, user_id, group_id):
    g = await groups_repository.get_owned(session, user_id, group_id)
    if g is None:
        raise HTTPException(status_code=404, detail="group not found")
    return g


async def get_group_detail(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> GroupDetail:
    g = await _ensure_visible(session, user_id, group_id)
    summary = await _summary(session, g, user_id)
    gms = await groups_repository.list_members(session, group_id)
    user_ids = [gm.user_id for gm in gms]
    users_map = {
        u.id: u for u in (await session.execute(
            select(User).where(User.id.in_(user_ids))
        )).scalars()
    }
    members = [
        GroupMemberRead(
            user_id=gm.user_id,
            username=users_map[gm.user_id].username,
            joined_at=gm.joined_at,
        ) for gm in gms
    ]
    return GroupDetail(**summary.model_dump(), members=members)


async def update_group(
    session: AsyncSession, user_id: UUID, group_id: UUID, body: GroupUpdate
) -> GroupSummary:
    g = await _ensure_owned(session, user_id, group_id)
    fields = body.model_dump(exclude_unset=True)
    updated = await groups_repository.update(session, g, fields)
    return await _summary(session, updated, user_id)


async def delete_group(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> None:
    if not await groups_repository.delete(session, user_id, group_id):
        raise HTTPException(status_code=404, detail="group not found")


async def add_member_by_username(
    session: AsyncSession, user_id: UUID, group_id: UUID, body: GroupAddMember
) -> GroupMemberRead:
    await _ensure_owned(session, user_id, group_id)
    user = await _user_by_username(session, body.username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    existing = await groups_repository.get_member(session, group_id, user.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="already a member")
    gm = await groups_repository.add_member(session, group_id, user.id)
    return GroupMemberRead(user_id=user.id, username=user.username, joined_at=gm.joined_at)


async def remove_member(
    session: AsyncSession, user_id: UUID, group_id: UUID, target_user_id: UUID
) -> None:
    g = await _ensure_visible(session, user_id, group_id)
    if target_user_id == g.owner_id:
        raise HTTPException(status_code=409, detail="cannot remove group owner")
    if user_id != g.owner_id and user_id != target_user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not await groups_repository.remove_member(session, group_id, target_user_id):
        raise HTTPException(status_code=404, detail="member not found")
