from __future__ import annotations
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transfer import TransferCreate, TransferRead
from app.services import transfers_service as svc

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.get("", response_model=list[TransferRead])
async def list_transfers(
    direction: Literal["incoming", "outgoing", "both"] = "both",
    status_filter: Literal["pending", "resolved", "all"] = "all",
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_transfers(
        session, user.id, direction=direction, status_filter=status_filter
    )


@router.post("", response_model=TransferRead, status_code=201)
async def create_transfer(
    body: TransferCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_transfer(session, user.id, body)


@router.post("/{transfer_id}/accept", response_model=TransferRead)
async def accept(
    transfer_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.accept_transfer(session, user.id, transfer_id)


@router.post("/{transfer_id}/reject", response_model=TransferRead)
async def reject(
    transfer_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.reject_transfer(session, user.id, transfer_id)


@router.post("/{transfer_id}/cancel", response_model=TransferRead)
async def cancel(
    transfer_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.cancel_transfer(session, user.id, transfer_id)
