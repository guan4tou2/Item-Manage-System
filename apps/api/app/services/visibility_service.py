from __future__ import annotations
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember
from app.models.user import User
from app.schemas.user import UserPublic


async def visible_item_owner_ids(
    session: AsyncSession, user_id: UUID
) -> set[UUID]:
    """Owner ids whose items the given user may read.

    = {user's own id} ∪ {user_ids of all fellow group members}
    """
    ids: set[UUID] = {user_id}
    own_groups = (await session.execute(
        select(GroupMember.group_id).where(GroupMember.user_id == user_id)
    )).scalars().all()
    if not own_groups:
        return ids
    stmt = select(GroupMember.user_id).where(
        GroupMember.group_id.in_(own_groups)
    )
    for uid in (await session.execute(stmt)).scalars():
        ids.add(uid)
    return ids


async def read_only_user_ids(
    session: AsyncSession, user_ids: Sequence[UUID]
) -> set[UUID]:
    """User ids that are read-only viewers (Phase 30).

    唯讀判定：使用者有 ≥1 筆 group membership，且**全部** membership 的 role
    皆為 `viewer`。推論：
    - 群組 owner 永遠不是唯讀（owner 建群時自身的 member row 為 editor；
      owner 事實來源是 `groups.owner_id`，權限檢查先判 owner 再判 role）。
    - 無任何群組的一般使用者不受影響。
    - 「A 群組 viewer、B 群組 editor」→ 可寫（避免被任一群組降權鎖死帳號）。
    - 離開所有群組 → 恢復可寫。
    """
    if not user_ids:
        return set()
    stmt = select(GroupMember.user_id, GroupMember.role).where(
        GroupMember.user_id.in_(list(user_ids))
    )
    roles_by_user: dict[UUID, set[str]] = {}
    for uid, role in (await session.execute(stmt)).all():
        roles_by_user.setdefault(uid, set()).add(role)
    return {uid for uid, roles in roles_by_user.items() if roles == {"viewer"}}


async def is_read_only(session: AsyncSession, user_id: UUID) -> bool:
    return bool(await read_only_user_ids(session, [user_id]))


async def user_public(session: AsyncSession, user: User) -> UserPublic:
    """UserPublic with `is_read_only` computed for the given user."""
    flagged = await read_only_user_ids(session, [user.id])
    return UserPublic.model_validate(user).model_copy(
        update={"is_read_only": user.id in flagged}
    )


async def user_public_many(
    session: AsyncSession, users: Sequence[User]
) -> list[UserPublic]:
    """Batch variant of `user_public` (single membership query)."""
    flagged = await read_only_user_ids(session, [u.id for u in users])
    return [
        UserPublic.model_validate(u).model_copy(
            update={"is_read_only": u.id in flagged}
        )
        for u in users
    ]
