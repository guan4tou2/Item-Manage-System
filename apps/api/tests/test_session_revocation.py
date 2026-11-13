"""Phase 44：session 撤銷（users.token_version）。

改密碼／登出所有裝置會遞增版本，既有 access／refresh token 立即失效；
沒有 `ver` 的舊 token 視為 0；PAT 不受影響。
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.models.favorite_audit_token import AuditLog
from app.models.user import User

PASSWORD = "secret1234"
NEW_PASSWORD = "newsecret567"


async def _login(client, username: str, password: str = PASSWORD) -> tuple[str, str]:
    """註冊＋登入，回傳 (access, refresh)。"""
    r = await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": password},
    )
    assert r.status_code == 201, r.text
    r = await client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"], r.cookies["refresh_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _me(client, access: str) -> int:
    return (await client.get("/api/auth/me", headers=_bearer(access))).status_code


async def _refresh(client, refresh: str):
    # 清掉 client 自動保存的 cookie，確保只送出指定的 refresh token。
    client.cookies.clear()
    client.cookies.set("refresh_token", refresh)
    try:
        return await client.post("/api/auth/refresh")
    finally:
        client.cookies.clear()


async def _user(test_engine, username: str) -> User:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        stmt = select(User).where(User.username == username)
        return (await session.execute(stmt)).scalar_one()


async def _audit(test_engine, action: str) -> list[AuditLog]:
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session:
        stmt = select(AuditLog).where(AuditLog.action == action)
        return list((await session.execute(stmt)).scalars().all())


def _legacy_token(user_id: str, token_type: str) -> str:
    """Phase 44 之前的 token 格式：沒有 `ver` claim。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    settings = get_settings()
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _b64decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# ---------------------------------------------------------------- 基本


async def test_new_user_starts_at_version_zero(client, test_engine):
    access, _ = await _login(client, "ver_zero")
    user = await _user(test_engine, "ver_zero")
    assert user.token_version == 0
    assert pyjwt.decode(access, options={"verify_signature": False})["ver"] == 0


async def test_logout_keeps_single_device_semantics(client):
    """/logout 只清 cookie，不遞增版本（D6）：access token 仍可用到過期。"""
    access, _ = await _login(client, "plain_logout")
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    assert await _me(client, access) == 200


# ---------------------------------------------------------------- 改密碼


async def test_change_password_revokes_old_tokens_and_reissues(client, test_engine):
    access, refresh = await _login(client, "pw_rev")
    # 另一台裝置的 session
    r = await client.post("/api/auth/login", json={"username": "pw_rev", "password": PASSWORD})
    other_access, other_refresh = r.json()["access_token"], r.cookies["refresh_token"]

    r = await client.post(
        "/api/users/me/change-password",
        headers=_bearer(access),
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["token_type"] == "bearer"
    new_access = body["access_token"]
    new_refresh = r.cookies["refresh_token"]
    assert (await _user(test_engine, "pw_rev")).token_version == 1

    # 舊 access／refresh（含其他裝置）全部失效
    for old in (access, other_access):
        assert await _me(client, old) == 401
    for old in (refresh, other_refresh):
        r = await _refresh(client, old)
        assert r.status_code == 401
        assert r.json()["detail"] == "token revoked"

    # 回應中的新 access 與新 cookie 可用（目前裝置不被登出）
    assert await _me(client, new_access) == 200
    r = await _refresh(client, new_refresh)
    assert r.status_code == 200
    assert await _me(client, r.json()["access_token"]) == 200


async def test_change_password_wrong_current_does_not_bump(client, test_engine):
    access, _ = await _login(client, "pw_keep")
    r = await client.post(
        "/api/users/me/change-password",
        headers=_bearer(access),
        json={"current_password": "nope", "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 422
    assert (await _user(test_engine, "pw_keep")).token_version == 0
    assert await _me(client, access) == 200


async def test_pat_survives_password_change(client):
    access, _ = await _login(client, "pat_keep")
    r = await client.post("/api/users/me/tokens", headers=_bearer(access), json={"name": "cron"})
    assert r.status_code == 201, r.text
    pat = r.json()["token"]
    assert pat.startswith("ims_pat_")

    r = await client.post(
        "/api/users/me/change-password",
        headers=_bearer(access),
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 200
    assert await _me(client, access) == 401
    assert await _me(client, pat) == 200


# ---------------------------------------------------------------- 登出所有裝置


async def test_logout_all_requires_auth(client):
    r = await client.post("/api/auth/logout-all")
    assert r.status_code == 401


async def test_logout_all_revokes_everything_and_audits(client, test_engine):
    access, refresh = await _login(client, "lo_all")
    user = await _user(test_engine, "lo_all")

    r = await client.post("/api/auth/logout-all", headers=_bearer(access))
    assert r.status_code == 204
    # refresh cookie 被清除（Set-Cookie 立即過期）
    set_cookie = r.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "Path=/api/auth" in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()

    assert (await _user(test_engine, "lo_all")).token_version == 1
    assert await _me(client, access) == 401
    assert (await _refresh(client, refresh)).status_code == 401

    rows = await _audit(test_engine, "auth.logout_all")
    assert len(rows) == 1
    assert rows[0].user_id == user.id
    assert rows[0].resource_type == "user"
    assert rows[0].resource_id == str(user.id)

    # 重新登入取得新版本 token
    r = await client.post("/api/auth/login", json={"username": "lo_all", "password": PASSWORD})
    assert r.status_code == 200
    assert await _me(client, r.json()["access_token"]) == 200


async def test_logout_all_with_revoked_token_is_rejected(client, test_engine):
    access, _ = await _login(client, "lo_twice")
    assert (await client.post("/api/auth/logout-all", headers=_bearer(access))).status_code == 204
    r = await client.post("/api/auth/logout-all", headers=_bearer(access))
    assert r.status_code == 401
    assert len(await _audit(test_engine, "auth.logout_all")) == 1


# ---------------------------------------------------------------- 舊格式 token 相容


async def test_legacy_token_without_ver_valid_until_bump(client, test_engine):
    access, _ = await _login(client, "legacy")
    user_id = str((await _user(test_engine, "legacy")).id)
    legacy_access = _legacy_token(user_id, "access")
    legacy_refresh = _legacy_token(user_id, "refresh")
    assert "ver" not in pyjwt.decode(legacy_access, options={"verify_signature": False})

    # 版本 0：舊 token 仍有效（升級不登出使用者）
    assert await _me(client, legacy_access) == 200
    r = await _refresh(client, legacy_refresh)
    assert r.status_code == 200
    assert await _me(client, r.json()["access_token"]) == 200

    # 遞增後失效
    assert (await client.post("/api/auth/logout-all", headers=_bearer(access))).status_code == 204
    assert await _me(client, legacy_access) == 401
    assert (await _refresh(client, legacy_refresh)).status_code == 401


async def test_tampered_ver_is_rejected_by_signature(client):
    """把舊 token 的 `ver` 改成新版本也沒用：簽章不符。"""
    access, _ = await _login(client, "tamper")
    assert (await client.post("/api/auth/logout-all", headers=_bearer(access))).status_code == 204
    assert await _me(client, access) == 401

    header, payload, signature = access.split(".")
    claims = json.loads(_b64decode(payload))
    claims["ver"] = 1
    forged = ".".join([header, _b64encode(json.dumps(claims).encode()), signature])
    r = await client.get("/api/auth/me", headers=_bearer(forged))
    assert r.status_code == 401
    assert r.json()["detail"] != "token revoked"  # 在簽章驗證就被擋下


@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
async def test_alg_none_and_wrong_algorithm_rejected_by_api(client, test_engine):
    await _login(client, "alg_user")
    user_id = str((await _user(test_engine, "alg_user")).id)
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "type": "access",
        "ver": 0,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    unsigned = ".".join(
        [
            _b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()),
            _b64encode(json.dumps(claims).encode()),
            "",
        ]
    )
    hs512 = pyjwt.encode(claims, get_settings().jwt_secret, algorithm="HS512")
    for token in (unsigned, hs512):
        assert await _me(client, token) == 401
