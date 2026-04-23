from __future__ import annotations
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group, GroupMember


async def create(session: AsyncSession, *, owner_id: UUID, name: str) -> Group:
    g = Group(owner_id=owner_id, name=name)
    session.add(g)
    await session.flush()
    session.add(GroupMember(group_id=g.id, user_id=owner_id))
    await session.commit()
    await session.refresh(g)
    return g


async def get_owned(session: AsyncSession, owner_id: UUID, group_id: UUID) -> Group | None:
    stmt = select(Group).where(Group.id == group_id, Group.owner_id == owner_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_for_member(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> Group | None:
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(Group.id == group_id, GroupMember.user_id == user_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: UUID) -> list[Group]:
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def member_count(session: AsyncSession, group_id: UUID) -> int:
    return int((await session.execute(
        select(func.count(GroupMember.id)).where(GroupMember.group_id == group_id)
    )).scalar_one())


async def update(session: AsyncSession, group: Group, fields: dict) -> Group:
    for k, v in fields.items():
        setattr(group, k, v)
    await session.commit()
    await session.refresh(group)
    return group


async def delete(session: AsyncSession, owner_id: UUID, group_id: UUID) -> bool:
    stmt = sa_delete(Group).where(Group.id == group_id, Group.owner_id == owner_id)
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0


async def list_members(session: AsyncSession, group_id: UUID) -> list[GroupMember]:
    stmt = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_member(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> GroupMember | None:
    stmt = select(GroupMember).where(
        GroupMember.group_id == group_id, GroupMember.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add_member(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> GroupMember:
    gm = GroupMember(group_id=group_id, user_id=user_id)
    session.add(gm)
    await session.commit()
    await session.refresh(gm)
    return gm


async def remove_member(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> bool:
    stmt = sa_delete(GroupMember).where(
        GroupMember.group_id == group_id, GroupMember.user_id == user_id
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
