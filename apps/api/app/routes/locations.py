from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.readonly import WriterGuardRoute
from app.db.session import get_db
from app.models.user import User
from app.schemas.location import (
    LocationCreate,
    LocationPath,
    LocationRead,
    LocationReorder,
    LocationTreeNode,
    LocationUpdate,
)
from app.services import locations_service

router = APIRouter(route_class=WriterGuardRoute, prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_locations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """平坦清單（走訪序）＋完整路徑——供樹狀選擇器與行動版扁平搜尋。"""
    return await locations_service.list_all(session, user.id)


@router.get("/tree", response_model=list[LocationTreeNode])
async def location_tree(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """巢狀樹（節點附直接物品數）——供 `/locations` 管理頁。"""
    return await locations_service.tree(session, user.id)


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await locations_service.create(session, user.id, body)


@router.post("/reorder", response_model=list[LocationRead])
async def reorder_locations(
    body: LocationReorder,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await locations_service.reorder(
        session, user.id, body.parent_id, body.location_ids
    )


@router.get("/{location_id}/path", response_model=LocationPath)
async def location_path(
    location_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await locations_service.path_of(session, user.id, location_id)


@router.patch("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: int,
    body: LocationUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """改名／改 kind／改排序／換 floor plan；帶 `parent_id` 時即為**搬移**。"""
    return await locations_service.update(session, user.id, location_id, body)


@router.delete(
    "/{location_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def delete_location(
    location_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await locations_service.delete(session, user.id, location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
