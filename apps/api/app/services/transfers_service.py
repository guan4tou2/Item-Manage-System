from __future__ import annotations
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.user import User
from app.repositories import (
    items_repository,
    loans_repository,
    transfers_repository,
)
from app.schemas.transfer import TransferCreate, TransferRead
from app.services import notifications_service


async def _to_read(session, t) -> TransferRead:
    rows = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_([t.from_user_id, t.to_user_id]))
    )).scalars()}
    item = (await session.execute(
        select(Item).where(Item.id == t.item_id)
    )).scalar_one_or_none()
    return TransferRead(
        id=t.id,
        item_id=t.item_id,
        item_name=item.name if item else "(deleted)",
        from_user_id=t.from_user_id,
        from_username=rows[t.from_user_id].username,
        to_user_id=t.to_user_id,
        to_username=rows[t.to_user_id].username,
        status=t.status,
        message=t.message,
        created_at=t.created_at,
        resolved_at=t.resolved_at,
    )


async def list_transfers(
    session, user_id, *, direction, status_filter,
) -> list[TransferRead]:
    rows = await transfers_repository.list_for_user(
        session, user_id, direction=direction, status=status_filter
    )
    return [await _to_read(session, r) for r in rows]


async def create_transfer(
    session: AsyncSession, user_id: UUID, body: TransferCreate
) -> TransferRead:
    item = await items_repository.get_owned(session, user_id, body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    recipient = (await session.execute(
        select(User).where(User.username == body.to_username)
    )).scalar_one_or_none()
    if recipient is None:
        raise HTTPException(status_code=404, detail="recipient not found")
    if recipient.id == user_id:
        raise HTTPException(status_code=422, detail="cannot transfer to self")
    existing = await transfers_repository.get_pending_for_item(session, body.item_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="item already has a pending transfer")
    active_loan = await loans_repository.get_active(session, body.item_id)
    if active_loan is not None:
        raise HTTPException(status_code=409, detail="item is currently on loan")

    t = await transfers_repository.create(
        session, item_id=body.item_id, from_user_id=user_id, to_user_id=recipient.id,
        message=body.message,
    )
    sender = (await session.execute(
        select(User).where(User.id == user_id)
    )).scalar_one()
    await notifications_service.emit(
        session,
        user_id=recipient.id,
        type="transfer.request",
        title=f"{sender.username} 想轉移「{item.name}」給你",
        body=body.message,
        link="/collaboration?tab=transfers",
    )
    return await _to_read(session, t)


async def _get_transfer_for_user(
    session, user_id: UUID, transfer_id: UUID, *, as_role: Literal["recipient", "sender"]
):
    t = await transfers_repository.get(session, transfer_id)
    if t is None:
        raise HTTPException(status_code=404, detail="transfer not found")
    if as_role == "recipient" and t.to_user_id != user_id:
        raise HTTPException(status_code=404, detail="transfer not found")
    if as_role == "sender" and t.from_user_id != user_id:
        raise HTTPException(status_code=404, detail="transfer not found")
    return t


async def accept_transfer(
    session: AsyncSession, user_id: UUID, transfer_id: UUID
) -> TransferRead:
    t = await _get_transfer_for_user(session, user_id, transfer_id, as_role="recipient")
    if t.status != "pending":
        raise HTTPException(status_code=409, detail="transfer already resolved")
    item = (await session.execute(
        select(Item).where(Item.id == t.item_id)
    )).scalar_one_or_none()
    if item is None or item.owner_id != t.from_user_id:
        raise HTTPException(status_code=409, detail="item no longer owned by sender")
    active_loan = await loans_repository.get_active(session, t.item_id)
    if active_loan is not None:
        raise HTTPException(status_code=409, detail="item is currently on loan")
    item.owner_id = t.to_user_id
    resolved = await transfers_repository.resolve(session, t, status="accepted")
    recipient = (await session.execute(
        select(User).where(User.id == t.to_user_id)
    )).scalar_one()
    await notifications_service.emit(
        session, user_id=t.from_user_id, type="transfer.accepted",
        title=f"{recipient.username} 已接受「{item.name}」的轉移",
        link="/collaboration?tab=transfers",
    )
    return await _to_read(session, resolved)


async def reject_transfer(
    session: AsyncSession, user_id: UUID, transfer_id: UUID
) -> TransferRead:
    t = await _get_transfer_for_user(session, user_id, transfer_id, as_role="recipient")
    if t.status != "pending":
        raise HTTPException(status_code=409, detail="transfer already resolved")
    resolved = await transfers_repository.resolve(session, t, status="rejected")
    return await _to_read(session, resolved)


async def cancel_transfer(
    session: AsyncSession, user_id: UUID, transfer_id: UUID
) -> TransferRead:
    t = await _get_transfer_for_user(session, user_id, transfer_id, as_role="sender")
    if t.status != "pending":
        raise HTTPException(status_code=409, detail="transfer already resolved")
    resolved = await transfers_repository.resolve(session, t, status="cancelled")
    return await _to_read(session, resolved)
