from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "lbl@t.io", "username": "label_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "label_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_item(client, auth, **extra):
    payload = {"name": "widget"}
    payload.update(extra)
    r = await client.post("/api/items", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ---- /api/items/{id}/qr.png -------------------------------------------


async def test_qr_png_returns_png_bytes(client, auth):
    item = await _create_item(client, auth)
    r = await client.get(f"/api/items/{item['id']}/qr.png", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    # PNG signature
    assert r.content.startswith(b"\x89PNG\r\n\x1a\n")
    # Non-trivial payload
    assert len(r.content) > 200


async def test_qr_png_requires_auth(client):
    r = await client.get("/api/items/00000000-0000-0000-0000-000000000000/qr.png")
    assert r.status_code == 401


async def test_qr_png_404_for_unknown_item(client, auth):
    r = await client.get(
        "/api/items/00000000-0000-0000-0000-000000000000/qr.png", headers=auth
    )
    assert r.status_code == 404


async def test_qr_png_404_for_other_owner(client, auth):
    item = await _create_item(client, auth)
    # register a second user
    await client.post(
        "/api/auth/register",
        json={"email": "lbl2@t.io", "username": "lbl_user_2", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "lbl_user_2", "password": "secret1234"},
    )
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    resp = await client.get(f"/api/items/{item['id']}/qr.png", headers=other)
    assert resp.status_code == 404


async def test_qr_png_404_after_soft_delete(client, auth):
    item = await _create_item(client, auth)
    await client.delete(f"/api/items/{item['id']}", headers=auth)
    r = await client.get(f"/api/items/{item['id']}/qr.png", headers=auth)
    assert r.status_code == 404


# ---- /api/items/{id}/label --------------------------------------------


async def test_label_endpoint_returns_metadata(client, auth):
    item = await _create_item(client, auth, name="我的相機", quantity=3)
    r = await client.get(f"/api/items/{item['id']}/label", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["item_id"] == item["id"]
    assert body["name"] == "我的相機"
    assert body["quantity"] == 3
    assert body["deep_link"].endswith(f"/items/{item['id']}")
    assert body["deep_link"].startswith("http")


async def test_label_uses_configured_public_url(client, auth, monkeypatch):
    monkeypatch.setenv("PUBLIC_WEB_URL", "https://ims.example.com")
    from app.config import get_settings
    get_settings.cache_clear()
    item = await _create_item(client, auth)
    r = await client.get(f"/api/items/{item['id']}/label", headers=auth)
    assert r.json()["deep_link"] == f"https://ims.example.com/items/{item['id']}"


async def test_label_requires_auth(client):
    r = await client.get("/api/items/00000000-0000-0000-0000-000000000000/label")
    assert r.status_code == 401


async def test_label_404_for_other_owner(client, auth):
    item = await _create_item(client, auth)
    await client.post(
        "/api/auth/register",
        json={"email": "lbl3@t.io", "username": "lbl_user_3", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "lbl_user_3", "password": "secret1234"},
    )
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}
    resp = await client.get(f"/api/items/{item['id']}/label", headers=other)
    assert resp.status_code == 404


# ---- render helper is deterministic-enough -----------------------------


def test_render_qr_png_pure_function_shape():
    from app.services.labels_service import render_qr_png

    png = render_qr_png("https://example.com/items/abc")
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 100
