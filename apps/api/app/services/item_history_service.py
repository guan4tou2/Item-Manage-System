from __future__ import annotations
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_history import ItemVersion, QuantityLog

logger = logging.getLogger(__name__)


async def log_quantity_change(
    session: AsyncSession,
    *,
    item_id: UUID,
    user_id: Optional[UUID],
    old_quantity: int,
    new_quantity: int,
    reason: Optional[str] = None,
) -> None:
    if old_quantity == new_quantity:
        return
    try:
        row = QuantityLog(
            item_id=item_id,
            user_id=user_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            reason=reason,
        )
        session.add(row)
        await session.commit()
    except Exception:
        logger.warning("quantity log insert failed", exc_info=True)


async def snapshot_version(
    session: AsyncSession,
    *,
    item_id: UUID,
    user_id: Optional[UUID],
    snapshot: dict[str, Any],
) -> None:
    try:
        row = ItemVersion(item_id=item_id, user_id=user_id, snapshot=snapshot)
        session.add(row)
        await session.commit()
    except Exception:
        logger.warning("item version insert failed", exc_info=True)


async def list_quantity_logs(
    session: AsyncSession, item_id: UUID, limit: int = 50
) -> list[QuantityLog]:
    stmt = (
        select(QuantityLog)
        .where(QuantityLog.item_id == item_id)
        .order_by(QuantityLog.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_item_versions(
    session: AsyncSession, item_id: UUID, limit: int = 50
) -> list[ItemVersion]:
    stmt = (
        select(ItemVersion)
        .where(ItemVersion.item_id == item_id)
        .order_by(ItemVersion.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
