from __future__ import annotations

from uuid import uuid4

import pytest


async def _login(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _member_auth(client, name: str, role: str) -> dict:
    """Register `name`, add as `role` member of a fresh group owned by another user."""
    owner = await _login(client, f"{name}_owner")
    member = await _login(client, name)
    gid = (
        await client.post("/api/groups", headers=owner, json={"name": f"g-{name}"})
    ).json()["id"]
    r = await client.post(
        f"/api/groups/{gid}/members",
        headers=owner,
        json={"username": name, "role": role},
    )
    assert r.status_code == 201
    return member


@pytest.fixture
async def viewer_auth(client):
    return await _member_auth(client, "guard_viewer", "viewer")


@pytest.fixture
async def editor_auth(client):
    return await _member_auth(client, "guard_editor", "editor")


JSON_WRITES = [
    ("POST", "/api/items"),
    ("PATCH", "/api/items/{id}"),
    ("DELETE", "/api/items/{id}"),
    ("POST", "/api/items/{id}/favorite"),
    ("PATCH", "/api/items/bulk"),
    ("POST", "/api/items/bulk-delete"),
    ("POST", "/api/items/{id}/batches"),
    ("POST", "/api/items/{id}/loans"),
    ("POST", "/api/lists"),
    ("POST", "/api/stocktakes"),
    ("POST", "/api/transfers"),
    ("POST", "/api/categories"),
    ("POST", "/api/locations"),
    ("POST", "/api/locations/reorder"),
    ("POST", "/api/warehouses"),
    ("POST", "/api/tags/{id}/merge"),
    ("POST", "/api/item-types"),
]

MULTIPART_WRITES = [
    ("POST", "/api/items/bulk-import"),
    ("POST", "/api/images"),
    ("POST", "/api/backup/import"),
]


def _resolve(url: str) -> str:
    return url.replace("{id}", str(uuid4()))


@pytest.mark.parametrize("method,url", JSON_WRITES, ids=[f"{m} {u}" for m, u in JSON_WRITES])
async def test_viewer_blocked_on_inventory_writes(client, viewer_auth, method, url):
    r = await client.request(method, _resolve(url), headers=viewer_auth, json={})
    assert r.status_code == 403, f"{method} {url} → {r.status_code}"


@pytest.mark.parametrize("method,url", MULTIPART_WRITES, ids=[f"{m} {u}" for m, u in MULTIPART_WRITES])
async def test_viewer_blocked_on_multipart_writes(client, viewer_auth, method, url):
    r = await client.request(
        method,
        _resolve(url),
        headers=viewer_auth,
        files={"file": ("x.csv", b"a,b\n", "text/csv")},
    )
    assert r.status_code == 403, f"{method} {url} → {r.status_code}"


@pytest.mark.parametrize("method,url", JSON_WRITES, ids=[f"{m} {u}" for m, u in JSON_WRITES])
async def test_editor_not_blocked_zero_regression(client, editor_auth, method, url):
    r = await client.request(method, _resolve(url), headers=editor_auth, json={})
    assert r.status_code != 403, f"{method} {url} → {r.status_code}"


async def test_unauthenticated_unchanged(client):
    assert (await client.post("/api/items", json={})).status_code == 401


async def test_reader_reads_unchanged(client, viewer_auth):
    assert (await client.get("/api/items", headers=viewer_auth)).status_code == 200
    assert (await client.get("/api/backup/export", headers=viewer_auth)).status_code == 200
    assert (await client.get("/api/items/export.csv", headers=viewer_auth)).status_code == 200
    # 讀取路徑不受防線影響：不存在的資源仍是 404，而非 403
    assert (await client.get(f"/api/items/{uuid4()}", headers=viewer_auth)).status_code == 404


async def test_reader_settings_writes_allowed(client, viewer_auth):
    r = await client.put(
        "/api/users/me/preferences", headers=viewer_auth, json={"theme": "dark"}
    )
    assert r.status_code == 200
    r = await client.patch(f"/api/notifications/{uuid4()}/read", headers=viewer_auth)
    assert r.status_code != 403
    r = await client.post("/api/users/me/tokens", headers=viewer_auth, json={"name": "t"})
    assert r.status_code != 403
