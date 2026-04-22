from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag


def normalize(name: str) -> str:
    return name.strip().lower()


async def list_for_owner(session: AsyncSession, owner_id: UUID, q: str | None = None) -> list[Tag]:
    stmt = select(Tag).where(Tag.owner_id == owner_id).order_by(Tag.name)
    if q:
        needle = normalize(q)
        stmt = stmt.where(Tag.name.ilike(f"{needle}%"))
    return list((await session.execute(stmt)).scalars().all())


async def get_by_name(session: AsyncSession, owner_id: UUID, name: str) -> Tag | None:
    stmt = select(Tag).where(Tag.owner_id == owner_id, Tag.name == normalize(name))
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_or_create_many(
    session: AsyncSession, owner_id: UUID, names: list[str]
) -> list[Tag]:
    result: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        n = normalize(raw)
        if not n or n in seen:
            continue
        seen.add(n)
        existing = await get_by_name(session, owner_id, n)
        if existing:
            result.append(existing)
        else:
            tag = Tag(owner_id=owner_id, name=n)
            session.add(tag)
            await session.flush()
            result.append(tag)
    return result
