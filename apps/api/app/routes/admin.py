from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserPublic
from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    users = await admin_service.list_users(session)
    return [UserPublic.model_validate(u) for u in users]


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    body: UserAdminUpdate,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    updated = await admin_service.set_active(session, admin, user_id, body.is_active)
    return UserPublic.model_validate(updated)


@router.post("/users/{user_id}/test-notification")
async def send_test_notification(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await admin_service.send_test_notification(session, admin, user_id)
    return {"notified": True}
