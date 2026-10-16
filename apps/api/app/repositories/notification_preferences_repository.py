from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_preference import NotificationPreference as Pref


async def get_cell(
    session: AsyncSession, user_id: UUID, *, type: str, channel: str
) -> Pref | None:
    stmt = select(Pref).where(
        Pref.user_id == user_id, Pref.type == type, Pref.channel == channel
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: UUID) -> list[Pref]:
    stmt = select(Pref).where(Pref.user_id == user_id)
    return list((await session.execute(stmt)).scalars().all())


async def has_any(session: AsyncSession, user_id: UUID) -> bool:
    stmt = select(Pref.id).where(Pref.user_id == user_id).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def upsert(
    session: AsyncSession, user_id: UUID, *, type: str, channel: str, enabled: bool
) -> Pref:
    row = await get_cell(session, user_id, type=type, channel=channel)
    if row is None:
        row = Pref(user_id=user_id, type=type, channel=channel, enabled=enabled)
        session.add(row)
    else:
        row.enabled = enabled
    await session.flush()
    return row


async def delete_cell(
    session: AsyncSession, user_id: UUID, *, type: str, channel: str
) -> None:
    await session.execute(
        sa_delete(Pref).where(
            Pref.user_id == user_id, Pref.type == type, Pref.channel == channel
        )
    )


async def delete_all(session: AsyncSession, user_id: UUID) -> int:
    result = await session.execute(sa_delete(Pref).where(Pref.user_id == user_id))
    return int(result.rowcount or 0)
