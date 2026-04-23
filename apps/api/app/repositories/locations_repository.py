from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location


async def list_for_owner(session: AsyncSession, owner_id: UUID) -> list[Location]:
    stmt = (
        select(Location)
        .where(Location.owner_id == owner_id)
        .order_by(Location.sort_order, Location.floor, Location.room, Location.zone)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_owned(session: AsyncSession, owner_id: UUID, location_id: int) -> Location | None:
    stmt = select(Location).where(Location.id == location_id, Location.owner_id == owner_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(session: AsyncSession, owner_id: UUID, **fields) -> Location:
    loc = Location(owner_id=owner_id, **fields)
    session.add(loc)
    await session.commit()
    await session.refresh(loc)
    return loc


async def update(session: AsyncSession, loc: Location, **fields) -> Location:
    for k, v in fields.items():
        setattr(loc, k, v)
    await session.commit()
    await session.refresh(loc)
    return loc


async def delete(session: AsyncSession, loc: Location) -> None:
    await session.delete(loc)
    await session.commit()
