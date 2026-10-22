"""Phase 36 T1.1：位置 QR 標籤端點。

- `GET /api/locations/{id}/label` → 名稱／完整路徑／**含子孫**物品數／深連結
- `GET /api/locations/{id}/qr.png` → QR PNG（內容 = 深連結）
- 權限：本人位置；他人／不存在 → 404（不洩漏存在性）；未登入 → 401
"""
from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "loclbl@t.io", "username": "loclbl_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "loclbl_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_location(client, auth, name: str, parent_id: int | None = None) -> dict:
    body: dict = {"name": name}
    if parent_id is not None:
        body["parent_id"] = parent_id
    r = await client.post("/api/locations", headers=auth, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_item(client, auth, name: str, location_id: int) -> dict:
    r = await client.post(
        "/api/items",
        headers=auth,
        json={"name": name, "location_id": location_id},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---- /api/locations/{id}/label ------------------------------------------


async def test_location_label_returns_name_path_and_deep_link(client, auth):
    floor = await _create_location(client, auth, "1F")
    room = await _create_location(client, auth, "廚房", floor["id"])

    r = await client.get(f"/api/locations/{room['id']}/label", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["location_id"] == room["id"]
    assert body["name"] == "廚房"
    assert body["path"] == "1F / 廚房"
    assert body["deep_link"].endswith(f"/items?location={room['id']}")


async def test_location_label_item_count_includes_descendants(client, auth):
    floor = await _create_location(client, auth, "1F")
    room = await _create_location(client, auth, "廚房", floor["id"])
    box = await _create_location(client, auth, "藥箱", room["id"])

    await _create_item(client, auth, "感冒藥", box["id"])
    await _create_item(client, auth, "維他命", room["id"])

    parent = await client.get(f"/api/locations/{room['id']}/label", headers=auth)
    assert parent.status_code == 200
    assert parent.json()["item_count"] == 2  # 自己 + 子孫

    leaf = await client.get(f"/api/locations/{box['id']}/label", headers=auth)
    assert leaf.json()["item_count"] == 1


async def test_location_label_404_for_unknown_location(client, auth):
    r = await client.get("/api/locations/999999/label", headers=auth)
    assert r.status_code == 404


async def test_location_label_404_for_other_owner(client, auth):
    location = await _create_location(client, auth, "廚房")
    await client.post(
        "/api/auth/register",
        json={"email": "loclbl2@t.io", "username": "loclbl_other", "password": "secret1234"},
    )
    other = await client.post(
        "/api/auth/login",
        json={"username": "loclbl_other", "password": "secret1234"},
    )
    other_auth = {"Authorization": f"Bearer {other.json()['access_token']}"}

    r = await client.get(f"/api/locations/{location['id']}/label", headers=other_auth)
    assert r.status_code == 404


async def test_location_label_requires_auth(client):
    r = await client.get("/api/locations/1/label")
    assert r.status_code == 401


# ---- /api/locations/{id}/qr.png ------------------------------------------


async def test_location_qr_png_returns_png(client, auth):
    location = await _create_location(client, auth, "藥箱")
    r = await client.get(f"/api/locations/{location['id']}/qr.png", headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(r.content) > 200


async def test_location_qr_png_encodes_deep_link(client, auth, decode_qr):
    """QR 內容 = 位置深連結（掃碼器可辨識 → 導向該位置物品清單）。

    以 zxing-cpp **實際解碼**斷言內容（非近似比對）。
    """
    from app.services import labels_service

    location = await _create_location(client, auth, "藥箱")
    r = await client.get(f"/api/locations/{location['id']}/qr.png", headers=auth)
    assert r.status_code == 200

    assert decode_qr(r.content) == labels_service.location_deep_link(location["id"])
    assert decode_qr(r.content).endswith(f"/items?location={location['id']}")


async def test_location_qr_png_differs_per_location(client, auth):
    """不同位置 → 不同 QR（payload 含位置 id）。"""
    location = await _create_location(client, auth, "藥箱")
    other = await _create_location(client, auth, "冰箱")
    first_png = (
        await client.get(f"/api/locations/{location['id']}/qr.png", headers=auth)
    ).content
    second_png = (
        await client.get(f"/api/locations/{other['id']}/qr.png", headers=auth)
    ).content
    assert first_png != second_png


async def test_location_qr_png_404_for_other_owner(client, auth):
    location = await _create_location(client, auth, "廚房")
    await client.post(
        "/api/auth/register",
        json={"email": "loclbl3@t.io", "username": "loclbl_other3", "password": "secret1234"},
    )
    other = await client.post(
        "/api/auth/login",
        json={"username": "loclbl_other3", "password": "secret1234"},
    )
    other_auth = {"Authorization": f"Bearer {other.json()['access_token']}"}

    r = await client.get(f"/api/locations/{location['id']}/qr.png", headers=other_auth)
    assert r.status_code == 404


async def test_location_qr_png_requires_auth(client):
    r = await client.get("/api/locations/1/qr.png")
    assert r.status_code == 401
