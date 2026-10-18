"""月報端點（Phase 31）：只回傳登入者自己的報表。

- `GET /api/reports`：清單（period DESC，limit/offset）
- `GET /api/reports/{id}`：詳情；不存在或非本人一律 404（不洩漏存在性）
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.repositories import reports_repository
from app.schemas.reports import ReportListResponse, ReportPayload, ReportRead

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _to_read(row: Report) -> ReportRead:
    return ReportRead(
        id=row.id,
        period=row.period,
        generated_at=row.generated_at,
        payload=ReportPayload.model_validate(row.payload),
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    rows = await reports_repository.list_for_user(
        session, user.id, limit=limit, offset=offset
    )
    total = await reports_repository.count_for_user(session, user.id)
    return ReportListResponse(
        items=[_to_read(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReportRead:
    row = await reports_repository.get_owned(session, user.id, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    return _to_read(row)
