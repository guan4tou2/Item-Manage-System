from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from app.config import get_settings

TokenType = Literal["access", "refresh"]

#: Phase 44：session 版本 claim；與 `users.token_version` 比對以支援撤銷。
VERSION_CLAIM = "ver"


class TokenError(Exception):
    pass


def create_token(
    subject: str,
    ttl: timedelta,
    token_type: TokenType,
    *,
    version: int = 0,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        VERSION_CLAIM: version,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        # 明確限定演算法（RFC 8725 §2.1）：拒絕 `alg=none` 與任何非設定值的演算法。
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise TokenError(f"expected {expected_type} token, got {payload.get('type')}")
    return payload


def token_version(payload: dict[str, Any]) -> int:
    """取出 token 的 session 版本。

    Phase 44 之前簽發的 token 沒有 `ver`，視為 0（升級當下不登出使用者）；
    型別不合（含 bool）視為無效 token。
    """
    ver = payload.get(VERSION_CLAIM, 0)
    if isinstance(ver, bool) or not isinstance(ver, int):
        raise TokenError("invalid token version")
    return ver
