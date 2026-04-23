from __future__ import annotations
import pytest


async def _register_login(client, username):
    await client.post("/api/auth/register", json={
        "email": f"{username}@t.io", "username": username, "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={"username": username, "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def admin_auth(client):
    h = await _register_login(client, "audit_admin")
    r = await client.post("/api/auth/bootstrap-admin", headers=h)
    assert r.status_code == 200
    return h


async def test_audit_list_requires_admin(client):
    h = await _register_login(client, "regular")
    r = await client.get("/api/admin/audit-logs", headers=h)
    assert r.status_code == 403


async def test_audit_logs_captured_on_deactivate(client, admin_auth):
    victim = await _register_login(client, "victim")
    users = (await client.get("/api/admin/users", headers=admin_auth)).json()
    target = next(u for u in users if u["username"] == "victim")
    await client.patch(f"/api/admin/users/{target['id']}", headers=admin_auth, json={"is_active": False})

    logs = (await client.get("/api/admin/audit-logs", headers=admin_auth)).json()
    actions = [r["action"] for r in logs]
    assert "admin.user.set_active" in actions
