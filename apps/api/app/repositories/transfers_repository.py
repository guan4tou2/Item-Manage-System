from __future__ import annotations
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.transfer import ItemTransfer


async def create(
    session: AsyncSession, *,
    item_id: UUID, from_user_id: UUID, to_user_id: UUID,
    message: str | None = None,
) -> ItemTransfer:
    t = ItemTransfer(
        item_id=item_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        message=message,
        status="pending",
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def get(session: AsyncSession, transfer_id: UUID) -> ItemTransfer | None:
    return (await session.execute(
        select(ItemTransfer).where(ItemTransfer.id == transfer_id)
    )).scalar_one_or_none()


async def get_pending_for_item(
    session: AsyncSession, item_id: UUID
) -> ItemTransfer | None:
    stmt = select(ItemTransfer).where(
        ItemTransfer.item_id == item_id, ItemTransfer.status == "pending"
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: UUID,
    *,
    direction: Literal["incoming", "outgoing", "both"] = "both",
    status: Literal["pending", "resolved", "all"] = "all",
) -> list[ItemTransfer]:
    stmt = select(ItemTransfer)
    if direction == "incoming":
        stmt = stmt.where(ItemTransfer.to_user_id == user_id)
    elif direction == "outgoing":
        stmt = stmt.where(ItemTransfer.from_user_id == user_id)
    else:
        stmt = stmt.where(
            or_(
                ItemTransfer.from_user_id == user_id,
                ItemTransfer.to_user_id == user_id,
            )
        )
    if status == "pending":
        stmt = stmt.where(ItemTransfer.status == "pending")
    elif status == "resolved":
        stmt = stmt.where(ItemTransfer.status != "pending")
    stmt = stmt.order_by(ItemTransfer.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def resolve(
    session: AsyncSession, t: ItemTransfer,
    *, status: Literal["accepted", "rejected", "cancelled"],
) -> ItemTransfer:
    t.status = status
    t.resolved_at = _utcnow()
    await session.commit()
    await session.refresh(t)
    return t
