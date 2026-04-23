from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.repositories import locations_repository as repo
from app.schemas.location import LocationCreate, LocationUpdate


async def list_all(session: AsyncSession, owner_id: UUID) -> list[Location]:
    return await repo.list_for_owner(session, owner_id)


async def create(session: AsyncSession, owner_id: UUID, body: LocationCreate) -> Location:
    return await repo.create(session, owner_id, **body.model_dump())


async def update(
    session: AsyncSession, owner_id: UUID, location_id: int, body: LocationUpdate
) -> Location:
    loc = await repo.get_owned(session, owner_id, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")
    return await repo.update(session, loc, **body.model_dump(exclude_unset=True))


async def delete(session: AsyncSession, owner_id: UUID, location_id: int) -> None:
    loc = await repo.get_owned(session, owner_id, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")
    await repo.delete(session, loc)


async def reorder(
    session: AsyncSession, owner_id: UUID, location_ids: list[int]
) -> list[Location]:
    """Rewrite sort_order for all provided location_ids as 0..N.

    All ids must belong to owner. Ids not owned or not found raise 404.
    """
    if len(set(location_ids)) != len(location_ids):
        raise HTTPException(status_code=400, detail="duplicate location ids")
    owned = await repo.list_for_owner(session, owner_id)
    owned_by_id = {loc.id: loc for loc in owned}
    for loc_id in location_ids:
        if loc_id not in owned_by_id:
            raise HTTPException(status_code=404, detail=f"location {loc_id} not found")
    for index, loc_id in enumerate(location_ids):
        owned_by_id[loc_id].sort_order = index
    await session.commit()
    return await repo.list_for_owner(session, owner_id)
