from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt

from app.config import get_settings

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    pass


def create_token(subject: str, ttl: timedelta, token_type: TokenType) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise TokenError(f"expected {expected_type} token, got {payload.get('type')}")
    return payload
