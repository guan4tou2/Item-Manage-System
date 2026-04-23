from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.loan import LoanCreate, LoanRead
from app.services import loans_service as svc

router = APIRouter(prefix="/api/items/{item_id}/loans", tags=["loans"])


@router.get("", response_model=list[LoanRead])
async def list_loans(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_loans(session, user.id, item_id)


@router.post("", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
async def create_loan(
    item_id: UUID,
    body: LoanCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_loan(session, user.id, item_id, body)


@router.post("/{loan_id}/return", response_model=LoanRead)
async def mark_returned(
    item_id: UUID,
    loan_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.mark_returned(session, user.id, item_id, loan_id)


@router.delete(
    "/{loan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_loan(
    item_id: UUID,
    loan_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_loan(session, user.id, item_id, loan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
