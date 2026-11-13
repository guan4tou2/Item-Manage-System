from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import set_refresh_cookie
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.api_token import ApiTokenCreate, ApiTokenCreated, ApiTokenRead
from app.schemas.preferences import PreferencesRead, PreferencesUpdate
from app.schemas.user import (
    PasswordChange,
    PasswordChangeResponse,
    UserProfileUpdate,
    UserPublic,
)
from app.services import api_tokens_service, preferences_service, profile_service, visibility_service
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    return await visibility_service.user_public(session, user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    body: UserProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    updated = await profile_service.update_profile(session, user, body)
    return await visibility_service.user_public(session, updated)


@router.post("/me/change-password", response_model=PasswordChangeResponse)
async def change_password(
    body: PasswordChange,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PasswordChangeResponse:
    await profile_service.change_password(session, user, body)
    # 版本已遞增：重新簽發目前裝置的 token，避免改完密碼自己也被登出。
    service = AuthService(session)
    set_refresh_cookie(response, service.issue_refresh_token(user))
    return PasswordChangeResponse(access_token=service.issue_access_token(user))


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


@router.get("/me/tokens", response_model=list[ApiTokenRead])
async def list_my_tokens(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ApiTokenRead]:
    return await api_tokens_service.list_tokens(session, user.id)


@router.post("/me/tokens", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_my_token(
    body: ApiTokenCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApiTokenCreated:
    return await api_tokens_service.create_token(session, user.id, body)


@router.delete(
    "/me/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_my_token(
    token_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await api_tokens_service.delete_token(session, user.id, token_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
