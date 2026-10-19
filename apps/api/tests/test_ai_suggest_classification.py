from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.ai_usage import AiUsage


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_DAILY_QUOTA", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()


async def _login(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_history(client, headers: dict, owner: str) -> None:
    category = (
        await client.post("/api/categories", headers=headers, json={"name": "廚房用品"})
    ).json()
    location = (
        await client.post("/api/locations", headers=headers, json={"name": "廚房"})
    ).json()
    r = await client.post(
        "/api/items",
        headers=headers,
        json={
            "name": "陶瓷咖啡杯",
            "category_id": category["id"],
            "location_id": location["id"],
            "tag_names": ["咖啡"],
        },
    )
    assert r.status_code == 201


async def test_returns_history_suggestions(client, db_session):
    """不設 GEMINI_API_KEY 也能用（規則式、不消耗配額）。"""
    auth = await _login(client, "cls_api_a")
    await _seed_history(client, auth, "cls_api_a")

    r = await client.post(
        "/api/ai/suggest-classification", headers=auth, json={"name": "陶瓷咖啡杯"}
    )

    assert r.status_code == 200
    body = r.json()
    assert body["category"]["name"] == "廚房用品"
    assert body["category"]["item_count"] == 1
    assert body["category"]["score"] == 4
    assert body["location"]["name"] == "廚房"
    assert [tag["name"] for tag in body["tags"]] == ["咖啡"]

    # 純規則式：不寫 ai_usage（未呼叫 LLM）
    rows = (await db_session.execute(select(AiUsage))).scalars().all()
    assert rows == []


async def test_empty_history_returns_nulls(client):
    auth = await _login(client, "cls_api_b")

    r = await client.post(
        "/api/ai/suggest-classification", headers=auth, json={"name": "量子力學"}
    )

    assert r.status_code == 200
    assert r.json() == {"category": None, "location": None, "tags": []}


async def test_validation(client):
    auth = await _login(client, "cls_api_c")

    blank = await client.post(
        "/api/ai/suggest-classification", headers=auth, json={"name": ""}
    )
    assert blank.status_code == 422

    too_long = await client.post(
        "/api/ai/suggest-classification", headers=auth, json={"name": "x" * 201}
    )
    assert too_long.status_code == 422

    extra = await client.post(
        "/api/ai/suggest-classification",
        headers=auth,
        json={"name": "咖啡杯", "image_id": None},
    )
    assert extra.status_code == 422


async def test_only_own_data(client):
    owner = await _login(client, "cls_api_d")
    other = await _login(client, "cls_api_d_other")
    await _seed_history(client, other, "cls_api_d_other")

    r = await client.post(
        "/api/ai/suggest-classification", headers=owner, json={"name": "陶瓷咖啡杯"}
    )

    assert r.status_code == 200
    assert r.json() == {"category": None, "location": None, "tags": []}


async def test_viewer_allowed(client):
    viewer_owner = await _login(client, "cls_viewer_owner")
    viewer = await _login(client, "cls_viewer")
    gid = (
        await client.post(
            "/api/groups", headers=viewer_owner, json={"name": "g-cls-viewer"}
        )
    ).json()["id"]
    added = await client.post(
        f"/api/groups/{gid}/members",
        headers=viewer_owner,
        json={"username": "cls_viewer", "role": "viewer"},
    )
    assert added.status_code == 201

    r = await client.post(
        "/api/ai/suggest-classification", headers=viewer, json={"name": "咖啡杯"}
    )

    # 唯讀計算、不掛 WriterGuardRoute
    assert r.status_code == 200
