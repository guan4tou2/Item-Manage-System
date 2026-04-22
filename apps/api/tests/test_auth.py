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
