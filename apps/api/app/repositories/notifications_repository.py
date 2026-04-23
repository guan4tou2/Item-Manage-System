from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.notification import Notification


async def create(
    session: AsyncSession,
    *,
    user_id: UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id, type=type, title=title, body=body, link=link
    )
    session.add(n)
    await session.commit()
    await session.refresh(n)
    return n


async def list_paginated(
    session: AsyncSession,
    user_id: UUID,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[Notification], int, int]:
    base = select(Notification).where(Notification.user_id == user_id)
    count_base = select(func.count(Notification.id)).where(Notification.user_id == user_id)
    if unread_only:
        base = base.where(Notification.read_at.is_(None))
        count_base = count_base.where(Notification.read_at.is_(None))

    total = (await session.execute(count_base)).scalar_one()
    unread = (await session.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
    )).scalar_one()

    stmt = base.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), int(total), int(unread)


async def unread_count(session: AsyncSession, user_id: UUID) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    )
    return int((await session.execute(stmt)).scalar_one())


async def mark_read(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> Notification | None:
    stmt = select(Notification).where(
        Notification.id == notification_id, Notification.user_id == user_id
    )
    n = (await session.execute(stmt)).scalar_one_or_none()
    if n is None:
        return None
    if n.read_at is None:
        n.read_at = _utcnow()
        await session.commit()
        await session.refresh(n)
    return n


async def mark_all_read(session: AsyncSession, user_id: UUID) -> int:
    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=_utcnow())
    )
    result = await session.execute(stmt)
    await session.commit()
    return int(result.rowcount or 0)


async def delete(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> bool:
    stmt = sa_delete(Notification).where(
        Notification.id == notification_id, Notification.user_id == user_id
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
