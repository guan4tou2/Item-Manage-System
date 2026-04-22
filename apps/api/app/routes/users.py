from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.preferences import PreferencesRead, PreferencesUpdate
from app.services import preferences_service

router = APIRouter(prefix="/api/users", tags=["users"])


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
