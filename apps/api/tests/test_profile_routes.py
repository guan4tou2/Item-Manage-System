from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "p@t.io", "username": "p_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "p_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_get_me(client, auth):
    r = await client.get("/api/users/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["username"] == "p_user"


async def test_patch_me_email(client, auth):
    r = await client.patch("/api/users/me", headers=auth, json={"email": "new@t.io"})
    assert r.status_code == 200
    assert r.json()["email"] == "new@t.io"


async def test_patch_me_username_conflict(client, auth):
    await client.post("/api/auth/register", json={"email": "x@t.io", "username": "x_user", "password": "secret1234"})
    r = await client.patch("/api/users/me", headers=auth, json={"username": "x_user"})
    assert r.status_code == 409


async def test_change_password_success(client, auth):
    r = await client.post("/api/users/me/change-password", headers=auth, json={
        "current_password": "secret1234", "new_password": "newsecret567",
    })
    assert r.status_code == 200
    # login with new works
    r2 = await client.post("/api/auth/login", json={"username": "p_user", "password": "newsecret567"})
    assert r2.status_code == 200


async def test_change_password_wrong_current(client, auth):
    r = await client.post("/api/users/me/change-password", headers=auth, json={
        "current_password": "wrong", "new_password": "newsecret567",
    })
    assert r.status_code == 422


async def test_change_password_too_short(client, auth):
    r = await client.post("/api/users/me/change-password", headers=auth, json={
        "current_password": "secret1234", "new_password": "short",
    })
    assert r.status_code == 422


async def test_bootstrap_admin_first_succeeds(client, auth):
    r = await client.post("/api/auth/bootstrap-admin", headers=auth)
    assert r.status_code == 200
    assert r.json()["is_admin"] is True


async def test_bootstrap_admin_second_409(client, auth):
    await client.post("/api/auth/bootstrap-admin", headers=auth)
    # register another user, try bootstrap
    await client.post("/api/auth/register", json={"email": "o@t.io", "username": "o_user", "password": "secret1234"})
    r2 = await client.post("/api/auth/login", json={"username": "o_user", "password": "secret1234"})
    headers2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    r = await client.post("/api/auth/bootstrap-admin", headers=headers2)
    assert r.status_code == 409
