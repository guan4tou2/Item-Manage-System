from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expiry_alert import ExpiryAlert

ADVANCE_LEVELS: tuple[str, ...] = ("d30", "d7", "d0")


async def advance_levels_for(
    session: AsyncSession, batch_ids: list[UUID]
) -> set[tuple[UUID, str]]:
    """已發過的 (batch, 進階級別) 集合；`d30/d7/d0` 每批每級只發一次（不限日期）。"""
    if not batch_ids:
        return set()
    stmt = select(ExpiryAlert.batch_id, ExpiryAlert.level).where(
        ExpiryAlert.batch_id.in_(batch_ids),
        ExpiryAlert.level.in_(ADVANCE_LEVELS),
    )
    return {(row[0], row[1]) for row in (await session.execute(stmt)).all()}


async def expired_on(
    session: AsyncSession, batch_ids: list[UUID], on: date
) -> set[UUID]:
    """今日已送 `expired` 的批次集合（每日一次）。"""
    if not batch_ids:
        return set()
    stmt = select(ExpiryAlert.batch_id).where(
        ExpiryAlert.batch_id.in_(batch_ids),
        ExpiryAlert.level == "expired",
        ExpiryAlert.sent_on == on,
    )
    return set((await session.execute(stmt)).scalars().all())


async def create(
    session: AsyncSession, *, batch_id: UUID, level: str, sent_on: date
) -> ExpiryAlert | None:
    """新增 dedupe 列；並發衝突以 savepoint 吸收，回 None 表已存在（視為已送出）。"""
    row = ExpiryAlert(batch_id=batch_id, level=level, sent_on=sent_on)
    try:
        async with session.begin_nested():
            session.add(row)
    except IntegrityError:
        return None
    return row
