from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.location import LocationCreate, LocationRead, LocationUpdate
from app.services import locations_service

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_locations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[LocationRead]:
    locs = await locations_service.list_all(session, user.id)
    return [LocationRead.model_validate(loc) for loc in locs]


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LocationRead:
    loc = await locations_service.create(session, user.id, body)
    return LocationRead.model_validate(loc)


@router.patch("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: int,
    body: LocationUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LocationRead:
    loc = await locations_service.update(session, user.id, location_id, body)
    return LocationRead.model_validate(loc)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_location(
    location_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await locations_service.delete(session, user.id, location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
