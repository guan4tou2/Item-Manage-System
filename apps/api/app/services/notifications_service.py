from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories import notifications_repository as repo
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)

logger = logging.getLogger(__name__)


async def emit(
    session: AsyncSession,
    *,
    user_id: UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> Notification | None:
    """Create a notification. Swallows errors and returns None to avoid
    breaking the triggering transaction. Also best-effort delivers via
    external channels (email/LINE/Telegram/WebPush) if configured."""
    try:
        notif = await repo.create(
            session,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            link=link,
        )
    except Exception:
        logger.warning(
            "notification emit failed",
            exc_info=True,
            extra={"type": type, "user_id": str(user_id)},
        )
        return None

    # Fan out to external channels (fail-soft)
    try:
        from app.services.external_notifications import deliver_all
        await deliver_all(
            session,
            user_id=user_id,
            title=title,
            body=body or "",
            link=link,
        )
    except Exception:
        logger.warning("external delivery failed", exc_info=True)

    return notif


async def list_notifications(
    session: AsyncSession,
    user_id: UUID,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> NotificationListResponse:
    rows, total, unread = await repo.list_paginated(
        session, user_id, unread_only=unread_only, limit=limit, offset=offset
    )
    return NotificationListResponse(
        items=[NotificationRead.model_validate(r) for r in rows],
        total=total,
        unread_count=unread,
    )


async def get_unread_count(session: AsyncSession, user_id: UUID) -> UnreadCountResponse:
    return UnreadCountResponse(count=await repo.unread_count(session, user_id))


async def mark_read(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> NotificationRead | None:
    n = await repo.mark_read(session, user_id, notification_id)
    return NotificationRead.model_validate(n) if n is not None else None


async def mark_all_read(
    session: AsyncSession, user_id: UUID
) -> MarkAllReadResponse:
    return MarkAllReadResponse(marked=await repo.mark_all_read(session, user_id))


async def delete(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> bool:
    return await repo.delete(session, user_id, notification_id)
