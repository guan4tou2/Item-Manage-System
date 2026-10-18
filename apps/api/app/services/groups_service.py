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
from app.services import audit_service, visibility_service


async def _user_by_username(session: AsyncSession, username: str) -> User | None:
    return (await session.execute(
        select(User).where(User.username == username)
    )).scalar_one_or_none()


async def _my_role(
    session: AsyncSession, g, current_user_id: UUID, roles: dict[UUID, str] | None = None
) -> str:
    """Effective role of the current user in the group (owner checked first)."""
    if g.owner_id == current_user_id:
        return "owner"
    if roles is not None:
        return roles.get(g.id, "editor")
    row = await groups_repository.get_member(session, g.id, current_user_id)
    return row.role if row is not None else "editor"


async def _summary(
    session: AsyncSession,
    g,
    current_user_id: UUID,
    roles: dict[UUID, str] | None = None,
) -> GroupSummary:
    owner = (await session.execute(
        select(User).where(User.id == g.owner_id)
    )).scalar_one()
    count = await groups_repository.member_count(session, g.id)
    return GroupSummary(
        id=g.id, name=g.name, owner_id=g.owner_id, owner_username=owner.username,
        is_owner=(g.owner_id == current_user_id), member_count=count,
        created_at=g.created_at, updated_at=g.updated_at,
        my_role=await _my_role(session, g, current_user_id, roles),
    )


async def list_groups(session: AsyncSession, user_id: UUID) -> list[GroupSummary]:
    groups = await groups_repository.list_for_user(session, user_id)
    roles = await groups_repository.member_roles_for_user(session, user_id)
    return [await _summary(session, g, user_id, roles) for g in groups]


async def create_group(
    session: AsyncSession, owner_id: UUID, body: GroupCreate
) -> GroupSummary:
    if await visibility_service.is_read_only(session, owner_id):
        raise HTTPException(
            status_code=403, detail="read-only viewer cannot create groups"
        )
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


async def _ensure_managed(session, user_id, group_id):
    """群組管理權：owner 或 admin。非成員 → 404；editor/viewer → 403。

    權限檢查先判 owner（`groups.owner_id` 唯一事實來源），再判 role。
    """
    owned = await groups_repository.get_owned(session, user_id, group_id)
    if owned is not None:
        return owned
    g = await groups_repository.get_for_member(session, user_id, group_id)
    if g is None:
        raise HTTPException(status_code=404, detail="group not found")
    row = await groups_repository.get_member(session, group_id, user_id)
    if row is None or row.role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
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
            role="owner" if gm.user_id == g.owner_id else gm.role,
        ) for gm in gms
    ]
    return GroupDetail(**summary.model_dump(), members=members)


async def update_group(
    session: AsyncSession, user_id: UUID, group_id: UUID, body: GroupUpdate
) -> GroupSummary:
    g = await _ensure_managed(session, user_id, group_id)
    fields = body.model_dump(exclude_unset=True)
    updated = await groups_repository.update(session, g, fields)
    return await _summary(session, updated, user_id)


async def delete_group(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> None:
    g = await groups_repository.get_for_member(session, user_id, group_id)
    if g is None:
        raise HTTPException(status_code=404, detail="group not found")
    if g.owner_id != user_id:
        # 破壞性操作收緊：僅 owner 可刪群組（admin 亦不可）
        raise HTTPException(status_code=403, detail="forbidden")
    await groups_repository.delete(session, user_id, group_id)


async def add_member_by_username(
    session: AsyncSession, user_id: UUID, group_id: UUID, body: GroupAddMember
) -> GroupMemberRead:
    await _ensure_managed(session, user_id, group_id)
    user = await _user_by_username(session, body.username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    existing = await groups_repository.get_member(session, group_id, user.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="already a member")
    gm = await groups_repository.add_member(session, group_id, user.id, role=body.role)
    await audit_service.log(
        session,
        user_id=user_id,
        action="group.member_added",
        resource_type="group",
        resource_id=str(group_id),
        meta={"username": user.username, "role": gm.role},
    )
    return GroupMemberRead(
        user_id=user.id, username=user.username, joined_at=gm.joined_at, role=gm.role
    )


async def change_member_role(
    session: AsyncSession,
    user_id: UUID,
    group_id: UUID,
    target_user_id: UUID,
    role: str,
) -> GroupMemberRead:
    g = await _ensure_managed(session, user_id, group_id)
    if target_user_id == g.owner_id:
        raise HTTPException(status_code=409, detail="cannot change group owner role")
    target_user = await session.get(User, target_user_id)
    member = await groups_repository.get_member(session, group_id, target_user_id)
    if target_user is None or member is None:
        raise HTTPException(status_code=404, detail="member not found")
    old_role = member.role
    updated = await groups_repository.set_member_role(
        session, group_id, target_user_id, role
    )
    if old_role != role:
        await audit_service.log(
            session,
            user_id=user_id,
            action="group.member_role_changed",
            resource_type="group",
            resource_id=str(group_id),
            meta={"username": target_user.username, "from": old_role, "to": role},
        )
    return GroupMemberRead(
        user_id=target_user_id,
        username=target_user.username,
        joined_at=updated.joined_at,
        role=updated.role,
    )


async def remove_member(
    session: AsyncSession, user_id: UUID, group_id: UUID, target_user_id: UUID
) -> None:
    g = await groups_repository.get_for_member(session, user_id, group_id)
    if g is None:
        raise HTTPException(status_code=404, detail="group not found")
    if target_user_id == g.owner_id:
        raise HTTPException(status_code=409, detail="cannot remove group owner")
    if user_id != target_user_id:
        # 移除他人需管理權（owner 或 admin）；自己可隨時離開
        if g.owner_id != user_id:
            row = await groups_repository.get_member(session, group_id, user_id)
            if row is None or row.role != "admin":
                raise HTTPException(status_code=403, detail="forbidden")
    target_user = await session.get(User, target_user_id)
    if not await groups_repository.remove_member(session, group_id, target_user_id):
        raise HTTPException(status_code=404, detail="member not found")
    await audit_service.log(
        session,
        user_id=user_id,
        action="group.member_removed",
        resource_type="group",
        resource_id=str(group_id),
        meta={
            "username": target_user.username if target_user else None,
            "self": user_id == target_user_id,
        },
    )
