from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.item import ItemRead
from app.schemas.stats import (
    CategoryBucket,
    LocationBucket,
    OverviewStats,
    TagBucket,
)
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewStats)
async def overview(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OverviewStats:
    return await stats_service.get_overview(session, user.id)


@router.get("/by-category", response_model=list[CategoryBucket])
async def by_category(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CategoryBucket]:
    return await stats_service.get_by_category(session, user.id)


@router.get("/by-location", response_model=list[LocationBucket])
async def by_location(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[LocationBucket]:
    return await stats_service.get_by_location(session, user.id)


@router.get("/by-tag", response_model=list[TagBucket])
async def by_tag(
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TagBucket]:
    return await stats_service.get_by_tag(session, user.id, limit=limit)


@router.get("/recent", response_model=list[ItemRead])
async def recent(
    limit: int = Query(default=5, ge=1, le=20),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ItemRead]:
    return await stats_service.get_recent(session, user.id, limit=limit)
