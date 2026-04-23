from __future__ import annotations
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember


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
