import pytest

from app.services import auth_service as auth_service_module
from app.services.auth_service import AuthService, InvalidCredentials


async def test_register_creates_user_and_returns_tokens(client):
    resp = await client.post("/api/auth/register", json={
        "email": "alice@example.com",
        "username": "alice",
        "password": "secret1234",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["username"] == "alice"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


async def test_register_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "username": "dup1", "password": "secret1234"}
    await client.post("/api/auth/register", json=payload)
    resp = await client.post("/api/auth/register", json={**payload, "username": "dup2"})
    assert resp.status_code == 409


async def test_login_returns_access_token_and_sets_refresh_cookie(client):
    await client.post("/api/auth/register", json={
        "email": "bob@example.com", "username": "bob", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "bob", "password": "secret1234",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    cookies = resp.cookies
    assert "refresh_token" in cookies


async def test_login_wrong_password_rejected(client):
    await client.post("/api/auth/register", json={
        "email": "carol@example.com", "username": "carol", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "carol", "password": "wrong-pass",
    })
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_returns_user_when_authed(client):
    register = await client.post("/api/auth/register", json={
        "email": "dave@example.com", "username": "dave", "password": "secret1234",
    })
    access = register.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "dave"


async def test_refresh_issues_new_access_token(client):
    await client.post("/api/auth/register", json={
        "email": "eve@example.com", "username": "eve", "password": "secret1234",
    })
    login = await client.post("/api/auth/login", json={
        "username": "eve", "password": "secret1234",
    })
    refresh_cookie = login.cookies.get("refresh_token")
    resp = await client.post("/api/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_locks_account_after_five_failures(client):
    await client.post("/api/auth/register", json={
        "email": "locked@example.com",
        "username": "locked",
        "password": "secret1234",
    })

    for _ in range(5):
        resp = await client.post("/api/auth/login", json={
            "username": "locked",
            "password": "wrong-pass",
        })
        assert resp.status_code == 401

    blocked = await client.post("/api/auth/login", json={
        "username": "locked",
        "password": "wrong-pass",
    })
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "too many login attempts"
    retry_after = int(blocked.headers["retry-after"])
    assert 0 < retry_after <= 15 * 60

    # 鎖定期間即使密碼正確也不能繞過。
    still_blocked = await client.post("/api/auth/login", json={
        "username": "locked",
        "password": "secret1234",
    })
    assert still_blocked.status_code == 429


async def test_login_lockout_does_not_affect_other_accounts(client):
    await client.post("/api/auth/register", json={
        "email": "victim@example.com",
        "username": "victim",
        "password": "secret1234",
    })
    await client.post("/api/auth/register", json={
        "email": "bystander@example.com",
        "username": "bystander",
        "password": "secret1234",
    })

    for _ in range(6):
        await client.post("/api/auth/login", json={
            "username": "victim",
            "password": "wrong-pass",
        })

    resp = await client.post("/api/auth/login", json={
        "username": "bystander",
        "password": "secret1234",
    })
    assert resp.status_code == 200


async def test_unknown_username_is_locked_identically(client):
    for _ in range(5):
        resp = await client.post("/api/auth/login", json={
            "username": "no-such-account",
            "password": "wrong-pass",
        })
        assert resp.status_code == 401

    blocked = await client.post("/api/auth/login", json={
        "username": "no-such-account",
        "password": "wrong-pass",
    })

    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "too many login attempts"
    assert "retry-after" in blocked.headers


async def test_login_locks_source_ip_after_ten_failures(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.auth._client_ip", lambda _request: "203.0.113.50"
    )

    for index in range(10):
        resp = await client.post("/api/auth/login", json={
            "username": f"spray-{index}",
            "password": "wrong-pass",
        })
        assert resp.status_code == 401

    blocked = await client.post("/api/auth/login", json={
        "username": "fresh-user",
        "password": "wrong-pass",
    })
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) <= 60

    # 換一個來源 IP 就不受上一個 IP 的計數影響。
    monkeypatch.setattr(
        "app.routes.auth._client_ip", lambda _request: "203.0.113.51"
    )
    other_ip = await client.post("/api/auth/login", json={
        "username": "fresh-user-2",
        "password": "wrong-pass",
    })
    assert other_ip.status_code == 401


async def test_successful_login_resets_account_failures(client):
    await client.post("/api/auth/register", json={
        "email": "reset@example.com",
        "username": "reset",
        "password": "secret1234",
    })

    for _ in range(4):
        assert (await client.post("/api/auth/login", json={
            "username": "reset",
            "password": "wrong-pass",
        })).status_code == 401

    ok = await client.post("/api/auth/login", json={
        "username": "reset",
        "password": "secret1234",
    })
    assert ok.status_code == 200

    for _ in range(4):
        assert (await client.post("/api/auth/login", json={
            "username": "reset",
            "password": "wrong-pass",
        })).status_code == 401

    # 若成功登入沒有重置，這一筆會是第 9 次而直接被鎖；應仍是 401。
    assert (await client.post("/api/auth/login", json={
        "username": "reset",
        "password": "wrong-pass",
    })).status_code == 401
    assert (await client.post("/api/auth/login", json={
        "username": "reset",
        "password": "wrong-pass",
    })).status_code == 429


async def test_unknown_username_still_verifies_password(db_session, monkeypatch):
    calls: list[tuple[str, str]] = []

    def fake_verify(plain: str, hashed: str) -> bool:
        calls.append((plain, hashed))
        return False

    monkeypatch.setattr(auth_service_module, "verify_password", fake_verify)

    with pytest.raises(InvalidCredentials):
        await AuthService(db_session).authenticate(
            username="missing-user", password="secret1234"
        )

    assert len(calls) == 1
