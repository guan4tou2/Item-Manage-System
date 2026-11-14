from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.readonly import WriterGuardRoute
from app.db.session import get_db
from app.models.user import User
from app.schemas.batch import (
    BatchConsume,
    BatchConsumeResult,
    BatchConsumeSplit,
    BatchCreate,
    BatchRead,
    BatchUpdate,
)
from app.schemas.item import ItemRead
from app.services import batches_service as svc
from app.services import items_service

router = APIRouter(route_class=WriterGuardRoute, prefix="/api/items/{item_id}/batches", tags=["batches"])

#: FEFO 便捷消耗端點路徑不在 batches prefix 下（roadmap L253）
item_consume_router = APIRouter(prefix="/api/items/{item_id}", tags=["batches"])


@router.get("", response_model=list[BatchRead])
async def list_batches(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    batches = await svc.list_batches(session, user.id, item_id)
    return [BatchRead.from_batch(b) for b in batches]


@router.post("", response_model=BatchRead, status_code=status.HTTP_201_CREATED)
async def create_batch(
    item_id: UUID,
    body: BatchCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    batch = await svc.create_batch(
        session,
        user.id,
        item_id,
        quantity=body.quantity,
        expiry_date=body.expiry_date,
        received_at=body.received_at,
        note=body.note,
        unit_cost=body.unit_cost,
    )
    return BatchRead.from_batch(batch)


@router.post("/disable", response_model=ItemRead)
async def disable_tracking(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    item = await svc.disable_tracking(session, user.id, item_id)
    return items_service._to_read(item)


@router.patch("/{batch_id}", response_model=BatchRead)
async def update_batch(
    item_id: UUID,
    batch_id: UUID,
    body: BatchUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    fields = body.model_dump(exclude_unset=True)
    batch = await svc.update_batch(session, user.id, item_id, batch_id, **fields)
    return BatchRead.from_batch(batch)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    item_id: UUID,
    batch_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_batch(session, user.id, item_id, batch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{batch_id}/consume", response_model=BatchRead)
async def consume_from_batch(
    item_id: UUID,
    batch_id: UUID,
    body: BatchConsume,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    batch = await svc.consume_from_batch(session, user.id, item_id, batch_id, body.quantity)
    return BatchRead.from_batch(batch)


@item_consume_router.post("/consume", response_model=BatchConsumeResult)
async def consume_fefo(
    item_id: UUID,
    body: BatchConsume,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    split = await svc.consume_fefo(session, user.id, item_id, body.quantity)
    return BatchConsumeResult(
        consumed=[
            BatchConsumeSplit(batch_id=batch_id, quantity=qty)
            for batch_id, qty in split
        ]
    )
