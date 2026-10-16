from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "prefr@t.io", "username": "prefr_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "prefr_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


PREF_URL = "/api/notifications/preferences"


def _update(type: str, channel: str, enabled: bool) -> dict:
    return {"type": type, "channel": channel, "enabled": enabled}


async def test_get_default_snapshot(client, auth):
    r = await client.get(PREF_URL, headers=auth)
    assert r.status_code == 200
    body = r.json()

    assert len(body["types"]) == 11
    assert body["types"][0] == {"key": "low_stock", "group": "items", "locked": False}
    assert {"key": "group_invite", "group": "collab", "locked": True} in body["types"]
    assert {"key": "system", "group": "system", "locked": True} in body["types"]
    assert body["channels"] == ["in_app", "email", "line", "telegram", "web_push"]
    assert body["has_custom"] is False
    assert body["matrix"]["low_stock"] == {
        "in_app": True,
        "email": True,
        "line": True,
        "telegram": True,
        "web_push": True,
    }
    assert body["matrix"]["expired"]["email"] is False
    assert body["matrix"]["expired"]["in_app"] is True
    assert body["channel_availability"] == {
        "in_app": True,
        "email": True,
        "line": False,
        "telegram": False,
        "web_push": False,
    }


async def test_put_reflects_in_get_and_is_idempotent(client, auth):
    payload = {"updates": [_update("low_stock", "email", False)]}

    put = await client.put(PREF_URL, headers=auth, json=payload)
    assert put.status_code == 200
    assert put.json()["matrix"]["low_stock"]["email"] is False
    assert put.json()["has_custom"] is True

    # 冪等：重送相同 payload 結果不變
    again = await client.put(PREF_URL, headers=auth, json=payload)
    assert again.status_code == 200
    assert again.json()["has_custom"] is True
    assert again.json()["matrix"]["low_stock"]["email"] is False

    got = (await client.get(PREF_URL, headers=auth)).json()
    assert got["matrix"]["low_stock"]["email"] is False
    assert got["has_custom"] is True


async def test_put_back_to_default_clears_custom(client, auth):
    await client.put(
        PREF_URL, headers=auth, json={"updates": [_update("low_stock", "email", False)]}
    )
    r = await client.put(
        PREF_URL, headers=auth, json={"updates": [_update("low_stock", "email", True)]}
    )
    assert r.status_code == 200
    assert r.json()["has_custom"] is False
    assert r.json()["matrix"]["low_stock"]["email"] is True


async def test_put_empty_updates_is_noop(client, auth):
    r = await client.put(PREF_URL, headers=auth, json={"updates": []})
    assert r.status_code == 200
    assert r.json()["has_custom"] is False


async def test_put_unknown_type_422(client, auth):
    r = await client.put(
        PREF_URL, headers=auth, json={"updates": [_update("bogus", "email", False)]}
    )
    assert r.status_code == 422
    assert "bogus" in r.json()["detail"]


async def test_put_unknown_channel_422(client, auth):
    r = await client.put(
        PREF_URL, headers=auth, json={"updates": [_update("low_stock", "sms", False)]}
    )
    assert r.status_code == 422
    assert "sms" in r.json()["detail"]


@pytest.mark.parametrize("locked_type", ["system", "group_invite"])
async def test_put_locked_disable_422(client, auth, locked_type):
    r = await client.put(
        PREF_URL,
        headers=auth,
        json={"updates": [_update(locked_type, "in_app", False)]},
    )
    assert r.status_code == 422
    assert locked_type in r.json()["detail"]


async def test_put_locked_enable_is_noop(client, auth):
    r = await client.put(
        PREF_URL, headers=auth, json={"updates": [_update("system", "in_app", True)]}
    )
    assert r.status_code == 200
    assert r.json()["has_custom"] is False
    assert r.json()["matrix"]["system"]["in_app"] is True


async def test_delete_resets_all_overrides(client, auth):
    await client.put(
        PREF_URL, headers=auth, json={"updates": [_update("low_stock", "line", False)]}
    )
    r = await client.delete(PREF_URL, headers=auth)
    assert r.status_code == 200
    assert r.json()["has_custom"] is False
    assert r.json()["matrix"]["low_stock"]["line"] is True


async def test_prefers_requires_auth(client):
    assert (await client.get(PREF_URL)).status_code == 401
    assert (
        await client.put(PREF_URL, json={"updates": []})
    ).status_code == 401
    assert (await client.delete(PREF_URL)).status_code == 401


async def test_in_app_disabled_suppresses_low_stock_notification(client, auth):
    # 經 API 關閉 low_stock × in_app 後，觸發庫存門檻不應產生站內通知
    await client.put(
        PREF_URL, headers=auth, json={"updates": [_update("low_stock", "in_app", False)]}
    )

    create = await client.post(
        "/api/items",
        headers=auth,
        json={"name": "偏好測試盒", "quantity": 5, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    r = await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 1})
    assert r.status_code == 200

    lst = (await client.get("/api/notifications", headers=auth)).json()
    assert all(i["type"] != "low_stock" for i in lst["items"])
