from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate
from app.services import warehouses_service as svc

router = APIRouter(prefix="/api/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseRead])
async def list_warehouses(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_warehouses(session, user.id)


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_warehouse(session, user.id, body)


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(
    warehouse_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.get_warehouse(session, user.id, warehouse_id)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(
    warehouse_id: int,
    body: WarehouseUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.update_warehouse(session, user.id, warehouse_id, body)


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_warehouse(
    warehouse_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_warehouse(session, user.id, warehouse_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
