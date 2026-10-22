from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import AuditFacets, AuditFacetValue, AuditLogPage, AuditLogRead
from app.schemas.user import UserAdminUpdate, UserPublic
from app.services import admin_service, audit_service, visibility_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """未帶時區的 datetime 視為 UTC（避免 aware／naive 比較爆炸）。"""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _audit_query(
    *,
    action: Optional[str],
    resource_type: Optional[str],
    user_id: Optional[UUID],
    q: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
) -> audit_service.AuditQuery:
    start, end = _as_utc(created_from), _as_utc(created_to)
    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="invalid_date_range")
    return audit_service.AuditQuery(
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        q=q,
        created_from=start,
        created_to=end,
    )


def _to_read(row: audit_service.AuditRow) -> AuditLogRead:
    return AuditLogRead.model_validate(row.log).model_copy(
        update={"user_email": row.user_email}
    )


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    users = await admin_service.list_users(session)
    return await visibility_service.user_public_many(session, users)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    body: UserAdminUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    updated = await admin_service.set_active(session, admin, user_id, body.is_active)
    return await visibility_service.user_public(session, updated)


@router.post("/users/{user_id}/test-notification")
async def send_test_notification(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await admin_service.send_test_notification(session, admin, user_id)
    return {"notified": True}


@router.get("/audit-logs", response_model=AuditLogPage)
async def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None, max_length=80),
    resource_type: Optional[str] = Query(default=None, max_length=40),
    user_id: Optional[UUID] = None,
    q: Optional[str] = Query(default=None, max_length=200),
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> AuditLogPage:
    """稽核查詢（Phase 39）：篩選＋分頁＋全域列舉值。"""
    query = _audit_query(
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        q=q,
        created_from=created_from,
        created_to=created_to,
    )
    rows, total = await audit_service.query_logs(
        session, query, limit=limit, offset=offset
    )
    facet_counts = await audit_service.facets(session)
    return AuditLogPage(
        items=[_to_read(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
        facets=AuditFacets(
            actions=[
                AuditFacetValue(value=value, count=count)
                for value, count in facet_counts.actions
            ],
            resource_types=[
                AuditFacetValue(value=value, count=count)
                for value, count in facet_counts.resource_types
            ],
        ),
    )


@router.get("/audit-logs/export.csv")
async def export_audit_logs(
    action: Optional[str] = Query(default=None, max_length=80),
    resource_type: Optional[str] = Query(default=None, max_length=40),
    user_id: Optional[UUID] = None,
    q: Optional[str] = Query(default=None, max_length=200),
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """以當前篩選匯出 CSV（UTF-8 BOM；上限 `DEFAULT_EXPORT_MAX_ROWS` 列）。"""
    query = _audit_query(
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        q=q,
        created_from=created_from,
        created_to=created_to,
    )
    rows = await audit_service.export_rows(
        session, query, max_rows=audit_service.DEFAULT_EXPORT_MAX_ROWS
    )
    body = "\ufeff" + audit_service.build_csv(rows)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="audit-logs-{stamp}.csv"',
        },
    )
