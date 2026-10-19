"""Phase 34 T1.4：`POST /api/ai/search`。

- 成功：LLM 轉譯 → 白名單驗證 → 既有搜尋 API → `{filters, applied, items, total}`
- fallback：未設 key／配額耗盡／上游錯誤／轉譯失敗 → **200** 關鍵字搜尋
  （`fallback_reason`）；未呼叫 LLM 時**不扣配額**
- opt-in：未開啟 `ai_data_sharing_enabled` → 403 `ai_opt_in_required`
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.models.ai_usage import AiUsage


def _mock_gemini(monkeypatch, payload: dict | str) -> MagicMock:
    fake_response = MagicMock()
    fake_response.text = payload if isinstance(payload, str) else json.dumps(payload)
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)
    return fake_client


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AI_DAILY_QUOTA", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()


def _configure(monkeypatch, *, key: str | None, quota: int | None = None) -> None:
    if key is None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GEMINI_API_KEY", key)
    if quota is not None:
        monkeypatch.setenv("AI_DAILY_QUOTA", str(quota))
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


async def _opt_in(client, headers: dict) -> None:
    r = await client.put(
        "/api/users/me/preferences",
        headers=headers,
        json={"ai_data_sharing_enabled": True},
    )
    assert r.status_code == 200, r.text


async def _seed(client, headers: dict) -> dict:
    """分類「藥品」／位置「廚房」＋兩件物品（一件快過期）。"""
    from datetime import timedelta

    from app.clock import today_taipei

    category = (
        await client.post("/api/categories", headers=headers, json={"name": "藥品"})
    ).json()
    location = (
        await client.post("/api/locations", headers=headers, json={"name": "廚房"})
    ).json()
    medicine = (
        await client.post(
            "/api/items",
            headers=headers,
            json={
                "name": "感冒藥",
                "quantity": 1,
                "category_id": category["id"],
                "location_id": location["id"],
            },
        )
    ).json()
    await client.post(
        f"/api/items/{medicine['id']}/batches",
        headers=headers,
        json={"expiry_date": (today_taipei() + timedelta(days=3)).isoformat()},
    )
    await client.post(
        "/api/items",
        headers=headers,
        json={"name": "工具箱", "quantity": 1},
    )
    return {"category": category, "location": location, "medicine": medicine}


async def test_search_uses_llm_filters(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(
        monkeypatch,
        {"q": "藥", "location": "廚房", "expiry": "expiring_soon", "sort": "expiry_asc"},
    )
    auth = await _login(client, "srch_a")
    await _opt_in(client, auth)
    seeded = await _seed(client, auth)

    r = await client.post(
        "/api/ai/search", headers=auth, json={"query": "廚房裡快過期的藥"}
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fallback_reason"] is None
    assert body["filters"]["q"] == "藥"
    assert body["filters"]["location_id"] == seeded["location"]["id"]
    assert body["filters"]["expiry"] == "expiring_soon"
    assert body["applied"]["location"]["name"] == "廚房"
    assert body["applied"]["expiry"] == "expiring_soon"
    assert [i["name"] for i in body["items"]] == ["感冒藥"]
    assert body["total"] == 1


async def test_search_requires_opt_in(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch, {"q": "藥"})
    auth = await _login(client, "srch_b")

    r = await client.post("/api/ai/search", headers=auth, json={"query": "藥"})

    assert r.status_code == 403
    assert r.json()["detail"] == "ai_opt_in_required"


async def test_search_without_key_falls_back_to_keyword(client, monkeypatch, db_session):
    _configure(monkeypatch, key=None)
    auth = await _login(client, "srch_c")
    await _opt_in(client, auth)
    await _seed(client, auth)

    r = await client.post("/api/ai/search", headers=auth, json={"query": "感冒藥"})

    assert r.status_code == 200
    body = r.json()
    assert body["fallback_reason"] == "ai_disabled"
    assert body["filters"]["q"] == "感冒藥"
    assert body["filters"]["location_id"] is None
    assert [i["name"] for i in body["items"]] == ["感冒藥"]
    # 未呼叫 LLM → 不扣配額
    assert (await db_session.execute(select(AiUsage))).scalars().all() == []


async def test_search_quota_exhausted_falls_back(client, monkeypatch, db_session):
    _configure(monkeypatch, key="fake-key", quota=1)
    _mock_gemini(monkeypatch, {"q": "藥"})
    auth = await _login(client, "srch_d")
    await _opt_in(client, auth)
    await _seed(client, auth)
    # 先耗盡當日配額
    first = await client.post("/api/ai/search", headers=auth, json={"query": "藥"})
    assert first.status_code == 200
    assert first.json()["fallback_reason"] is None

    second = await client.post("/api/ai/search", headers=auth, json={"query": "感冒藥"})

    assert second.status_code == 200
    body = second.json()
    assert body["fallback_reason"] == "quota_exhausted"
    assert body["filters"]["q"] == "感冒藥"
    assert body["filters"]["location_id"] is None
    assert [i["name"] for i in body["items"]] == ["感冒藥"]


async def test_search_upstream_error_falls_back(client, monkeypatch):
    _configure(monkeypatch, key="fake-key")
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)
    auth = await _login(client, "srch_e")
    await _opt_in(client, auth)
    await _seed(client, auth)

    r = await client.post("/api/ai/search", headers=auth, json={"query": "感冒藥"})

    assert r.status_code == 200
    assert r.json()["fallback_reason"] == "upstream_error"
    assert [i["name"] for i in r.json()["items"]] == ["感冒藥"]


async def test_search_unparsed_response_falls_back_and_consumes_quota(
    client, monkeypatch, db_session
):
    _configure(monkeypatch, key="fake-key", quota=10)
    _mock_gemini(monkeypatch, "not json at all")
    auth = await _login(client, "srch_f")
    await _opt_in(client, auth)
    await _seed(client, auth)

    r = await client.post("/api/ai/search", headers=auth, json={"query": "感冒藥"})

    assert r.status_code == 200
    assert r.json()["fallback_reason"] == "unparsed"
    usage = (await db_session.execute(select(AiUsage))).scalars().all()
    assert len(usage) == 1 and usage[0].calls == 1


async def test_search_drops_foreign_ids_and_reports_unresolved(client, monkeypatch):
    """LLM 嘗試指定他人／不存在的名稱 → 丟棄並回報，不影響其他條件。"""
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(
        monkeypatch,
        {"category": "別人的分類", "location": "不存在的房間", "q": "藥"},
    )
    auth = await _login(client, "srch_g")
    await _opt_in(client, auth)
    await _seed(client, auth)

    r = await client.post("/api/ai/search", headers=auth, json={"query": "藥"})

    assert r.status_code == 200
    body = r.json()
    assert body["filters"]["q"] == "藥"
    assert body["filters"]["category_id"] is None
    assert body["unresolved"] == ["category:別人的分類", "location:不存在的房間"]


async def test_search_empty_filters_falls_back(client, monkeypatch):
    """LLM 回空物件 → 無條件可用 → 走關鍵字 fallback（避免全表掃描）。"""
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch, {})
    auth = await _login(client, "srch_h")
    await _opt_in(client, auth)
    await _seed(client, auth)

    r = await client.post("/api/ai/search", headers=auth, json={"query": "感冒藥"})

    assert r.status_code == 200
    assert r.json()["fallback_reason"] == "unparsed"
    assert [i["name"] for i in r.json()["items"]] == ["感冒藥"]


async def test_search_ignores_injected_fields(client, monkeypatch):
    """注入樣本：LLM 輸出含 owner_id／sql／ids → 一律忽略。"""
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(
        monkeypatch,
        {
            "q": "藥",
            "owner_id": "00000000-0000-0000-0000-000000000000",
            "sql": "DROP TABLE items",
            "ids": ["x"],
            "page": 99,
        },
    )
    auth = await _login(client, "srch_i")
    await _opt_in(client, auth)
    await _seed(client, auth)

    r = await client.post("/api/ai/search", headers=auth, json={"query": "藥"})

    assert r.status_code == 200
    assert r.json()["filters"]["q"] == "藥"
    # 契約只含白名單欄位（注入欄位不存在）
    assert set(r.json()["filters"]) == {
        "q",
        "category_id",
        "location_id",
        "tag_ids",
        "expiry",
        "loan",
        "favorite",
        "min_quantity",
        "max_quantity",
        "sort",
    }
    assert r.json()["fallback_reason"] is None


async def test_search_viewer_can_use(client, monkeypatch):
    """唯讀使用者也能搜尋（不掛 writer guard）。"""
    _configure(monkeypatch, key="fake-key")
    _mock_gemini(monkeypatch, {"q": "藥"})
    owner = await _login(client, "srch_j_owner")
    viewer = await _login(client, "srch_j_viewer")
    gid = (
        await client.post("/api/groups", headers=owner, json={"name": "g-srch"})
    ).json()["id"]
    assert (
        await client.post(
            f"/api/groups/{gid}/members",
            headers=owner,
            json={"username": "srch_j_viewer", "role": "viewer"},
        )
    ).status_code == 201
    await _opt_in(client, viewer)

    r = await client.post("/api/ai/search", headers=viewer, json={"query": "藥"})

    assert r.status_code == 200


async def test_search_rejects_blank_or_too_long_query(client):
    auth = await _login(client, "srch_k")
    await _opt_in(client, auth)

    assert (
        await client.post("/api/ai/search", headers=auth, json={"query": "   "})
    ).status_code == 422
    assert (
        await client.post("/api/ai/search", headers=auth, json={"query": "x" * 301})
    ).status_code == 422
