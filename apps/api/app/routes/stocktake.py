from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.stocktake import (
    StocktakeCreate,
    StocktakeDetail,
    StocktakeItemRead,
    StocktakeItemScan,
    StocktakeRead,
)
from app.services import stocktake_service as svc

router = APIRouter(prefix="/api/stocktakes", tags=["stocktake"])


@router.get("", response_model=list[StocktakeRead])
async def list_stocktakes(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_stocktakes(session, user.id)


@router.post("", response_model=StocktakeRead, status_code=status.HTTP_201_CREATED)
async def create_stocktake(
    body: StocktakeCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_stocktake(session, user.id, body)


@router.get("/{stocktake_id}", response_model=StocktakeDetail)
async def get_stocktake(
    stocktake_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.get_stocktake_detail(session, user.id, stocktake_id)


@router.post("/{stocktake_id}/scan", response_model=StocktakeItemRead)
async def scan_item(
    stocktake_id: UUID,
    body: StocktakeItemScan,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.scan_item(session, user.id, stocktake_id, body)


@router.post("/{stocktake_id}/complete", response_model=StocktakeDetail)
async def complete_stocktake(
    stocktake_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.complete_stocktake(session, user.id, stocktake_id)


@router.post("/{stocktake_id}/cancel", response_model=StocktakeRead)
async def cancel_stocktake(
    stocktake_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.cancel_stocktake(session, user.id, stocktake_id)
