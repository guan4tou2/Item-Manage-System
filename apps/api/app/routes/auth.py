from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import TokenError, decode_token
from app.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExists,
    InvalidCredentials,
    UsernameAlreadyExists,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=token,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.environment != "dev",
        samesite="lax",
        path="/api/auth",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, response: Response, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(session)
    try:
        user = await service.register(
            email=payload.email, username=payload.username, password=payload.password
        )
    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="email already registered")
    except UsernameAlreadyExists:
        raise HTTPException(status_code=409, detail="username already taken")
    access = service.issue_access_token(user)
    refresh = service.issue_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, response: Response, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(session)
    try:
        user = await service.authenticate(username=payload.username, password=payload.password)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="invalid credentials")
    access = service.issue_access_token(user)
    refresh = service.issue_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, user=UserPublic.model_validate(user))


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="missing refresh cookie")
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    from uuid import UUID

    service = AuthService(session)
    user = await service.get_user_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found")
    access = service.issue_access_token(user)
    new_refresh = service.issue_refresh_token(user)
    _set_refresh_cookie(response, new_refresh)
    return AccessTokenResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> Response:
    response.delete_cookie("refresh_token", path="/api/auth")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
