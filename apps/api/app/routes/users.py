from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.preferences import PreferencesRead, PreferencesUpdate
from app.schemas.user import PasswordChange, UserProfileUpdate, UserPublic
from app.services import preferences_service, profile_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: UserProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    updated = await profile_service.update_profile(session, user, body)
    return UserPublic.model_validate(updated)


@router.post("/me/change-password")
async def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await profile_service.change_password(session, user, body)
    return {"success": True}


@router.get("/me/preferences", response_model=PreferencesRead)
async def get_my_preferences(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PreferencesRead:
    return await preferences_service.get_preferences(session, user_id=user.id)


@router.put("/me/preferences", response_model=PreferencesRead)
async def update_my_preferences(
    update: PreferencesUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PreferencesRead:
    return await preferences_service.update_preferences(
        session, user_id=user.id, update=update
    )
