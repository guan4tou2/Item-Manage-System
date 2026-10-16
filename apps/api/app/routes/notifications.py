from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)
from app.schemas.notification_preferences import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
)
from app.services import notification_prefs as prefs_svc
from app.services import notifications_service as svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    return await svc.list_notifications(
        session, user.id, unread_only=unread_only, limit=limit, offset=offset
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    return await svc.get_unread_count(session, user.id)


# 偏好路由必須先於 DELETE /{notification_id} 宣告（"preferences" 會被
# UUID 路徑參數攔截而回 422）。
@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    return NotificationPreferencesResponse.model_validate(
        await prefs_svc.get_snapshot(session, user.id)
    )


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(
    payload: NotificationPreferencesUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    try:
        snapshot = await prefs_svc.apply_updates(
            session, user.id, [u.model_dump() for u in payload.updates]
        )
    except prefs_svc.PreferenceUpdateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return NotificationPreferencesResponse.model_validate(snapshot)


@router.delete("/preferences", response_model=NotificationPreferencesResponse)
async def reset_preferences(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    return NotificationPreferencesResponse.model_validate(
        await prefs_svc.reset(session, user.id)
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationRead:
    n = await svc.mark_read(session, user.id, notification_id)
    if n is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return n


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_read(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MarkAllReadResponse:
    return await svc.mark_all_read(session, user.id)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_notification(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    if not await svc.delete(session, user.id, notification_id):
        raise HTTPException(status_code=404, detail="notification not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
