from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import clear_refresh_cookie, set_refresh_cookie
from app.auth.dependencies import get_current_user
from app.auth.jwt import TokenError, decode_token, token_version
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic
from app.services import (
    audit_service,
    login_throttle_service,
    notifications_service,
    visibility_service,
)
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExists,
    InvalidCredentials,
    UsernameAlreadyExists,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    """取得來源 IP；uvicorn 的 proxy headers 會把 nginx 後方的真實 IP 放進 client。"""
    return request.client.host if request.client else "unknown"


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
    await notifications_service.emit(
        session,
        user_id=user.id,
        type="system.welcome",
        title="歡迎使用 IMS",
        body="從儀表板開始管理你的物品吧。",
        link="/dashboard",
    )
    access = service.issue_access_token(user)
    refresh = service.issue_refresh_token(user)
    set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access, user=await visibility_service.user_public(session, user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={429: {"description": "Too many login attempts"}},
)
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    ip = _client_ip(request)
    status = await login_throttle_service.check(
        session, username=payload.username, ip=ip
    )
    if status.blocked:
        # 不執行密碼驗證；對未知帳號與既有帳號使用同一個回應。
        raise HTTPException(
            status_code=429,
            detail="too many login attempts",
            headers={"Retry-After": str(status.retry_after_seconds)},
        )

    service = AuthService(session)
    try:
        user = await service.authenticate(username=payload.username, password=payload.password)
    except InvalidCredentials:
        await login_throttle_service.record_failure(
            session, username=payload.username, ip=ip
        )
        # 只記「既有帳號」的失敗（陌生帳號不寫，避免匿名灌寫／列舉訊號）；
        # 同一帳號在時間窗內只記一筆（見 audit_service.log_login_failure）。
        existing = await service.get_user_by_username(payload.username)
        if existing is not None:
            await audit_service.log_login_failure(
                session, user_id=existing.id, username=existing.username
            )
        raise HTTPException(status_code=401, detail="invalid credentials")
    await login_throttle_service.reset_account(
        session, username=payload.username
    )
    access = service.issue_access_token(user)
    refresh = service.issue_refresh_token(user)
    set_refresh_cookie(response, refresh)
    await audit_service.log(
        session,
        user_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
    )
    return TokenResponse(
        access_token=access, user=await visibility_service.user_public(session, user)
    )


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
        version = token_version(payload)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    from uuid import UUID

    service = AuthService(session)
    user = await service.get_user_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="user not found")
    # Phase 44：撤銷後（改密碼／登出所有裝置）舊 refresh token 不能再換新 token。
    if version != user.token_version:
        raise HTTPException(status_code=401, detail="token revoked")
    access = service.issue_access_token(user)
    new_refresh = service.issue_refresh_token(user)
    set_refresh_cookie(response, new_refresh)
    return AccessTokenResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> Response:
    clear_refresh_cookie(response)
    response.status_code = 204
    return response


@router.post("/logout-all", status_code=204)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """登出所有裝置：遞增 session 版本，所有既有 access／refresh token 失效。

    PAT（`ims_pat_`）不受影響，需另行在權杖管理刪除（Phase 44 D8）。
    """
    await AuthService(session).revoke_all_sessions(current_user)
    clear_refresh_cookie(response)
    # 主寫入已 commit，才寫稽核（audit_service.log 為 fail-soft）。
    await audit_service.log(
        session,
        user_id=current_user.id,
        action="auth.logout_all",
        resource_type="user",
        resource_id=str(current_user.id),
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=UserPublic)
async def me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    return await visibility_service.user_public(session, current_user)


@router.post("/bootstrap-admin", response_model=UserPublic)
async def bootstrap_admin(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserPublic:
    from app.services import profile_service
    promoted = await profile_service.bootstrap_admin_if_none(session, current_user)
    return await visibility_service.user_public(session, promoted)
