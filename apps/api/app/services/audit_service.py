from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite_audit_token import AuditLog

logger = logging.getLogger(__name__)


async def log(
    session: AsyncSession,
    *,
    user_id: Optional[UUID],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Insert an audit log row. Fail-soft like notifications_service.emit."""
    try:
        row = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            meta=meta,
        )
        session.add(row)
        await session.commit()
    except Exception:
        logger.warning("audit log insert failed", exc_info=True)


async def list_logs(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type is not None:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    stmt = stmt.limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())
