from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_raw_preferences(session: AsyncSession, user_id: UUID) -> dict:
    stmt = select(User.preferences).where(User.id == user_id)
    result = await session.execute(stmt)
    value = result.scalar_one_or_none()
    return value or {}


async def set_raw_preferences(
    session: AsyncSession, user_id: UUID, value: dict
) -> dict:
    stmt = select(User).where(User.id == user_id)
    user = (await session.execute(stmt)).scalar_one()
    user.preferences = value
    await session.flush()
    await session.commit()
    await session.refresh(user)
    return user.preferences
