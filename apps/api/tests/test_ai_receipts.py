"""AI 收據辨識（Phase 33）：抽取層與端點。

LLM 一律以 mock `google.genai.Client` 取代（CI 無 key、不呼叫外網）。
"""
from __future__ import annotations

import io
import json
import struct
import zlib
from decimal import Decimal
from unittest.mock import MagicMock

import pytest


def _tiny_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00\xff\x00")
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(autouse=True)
def _media_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "rc@t.io", "username": "receipt_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "receipt_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _gemini(monkeypatch, payload, *, text: str | None = None) -> MagicMock:
    """以 mock Client 回傳指定 JSON（`text` 可覆寫原始字串）。"""
    fake_response = MagicMock()
    fake_response.text = text if text is not None else json.dumps(payload)
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)
    return fake_client


def _receipt_payload(items=None) -> dict:
    return {
        "merchant": "全聯福利中心",
        "purchased_at": "2026-10-18",
        "currency": "TWD",
        "total": "1250.00",
        "items": items
        if items is not None
        else [
            {
                "name": "鮮乳",
                "quantity": 2,
                "unit_price": "62.00",
                "subtotal": "124.00",
            },
            {
                "name": "衛生紙",
                "quantity": 1,
                "unit_price": "199.00",
                "subtotal": "199.00",
            },
        ],
    }


# --- Phase 38：抽取擴充（折扣／稅／運費／不確定欄位）--------------------


def test_parse_receipt_reads_receipt_level_amounts():
    """收據層級：subtotal／discount／tax／shipping（Phase 38）。"""
    from app.services import ai_service

    payload = _receipt_payload()
    payload.update(
        {
            "subtotal": "323.00",
            "discount": "20.00",
            "tax": "16.15",
            "shipping": "30.00",
        }
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.subtotal == Decimal("323.00")
    assert result.discount == Decimal("20.00")
    assert result.tax == Decimal("16.15")
    assert result.shipping == Decimal("30.00")


def test_parse_receipt_reads_item_level_amounts():
    from app.services import ai_service

    payload = _receipt_payload(
        items=[
            {
                "name": "鮮乳",
                "quantity": 2,
                "unit_price": "62.00",
                "subtotal": "124.00",
                "discount": "10.00",
                "tax": "5.00",
            }
        ]
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.items[0].discount == Decimal("10.00")
    assert result.items[0].tax == Decimal("5.00")


def test_parse_receipt_missing_new_fields_are_none():
    """舊格式回應（無新欄位）仍可解析 → 向後相容。"""
    from app.services import ai_service

    result = ai_service.parse_receipt_response(json.dumps(_receipt_payload()))

    assert result.subtotal is None
    assert result.discount is None
    assert result.tax is None
    assert result.shipping is None
    assert result.uncertain_fields == []
    assert result.items[0].discount is None


def test_parse_receipt_filters_unknown_uncertain_fields():
    """不確定欄位只接受白名單路徑（D5）。"""
    from app.services import ai_service

    payload = _receipt_payload()
    payload["uncertain_fields"] = [
        "total",
        "currency",
        "items[0].quantity",
        "items[0].unit_price",
        "items[0].bogus",
        "items[x].name",
        "secret_field",
        "total",  # 重複
    ]

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.uncertain_fields == [
        "total",
        "currency",
        "items[0].quantity",
        "items[0].unit_price",
    ]


def test_parse_receipt_uncertain_fields_ignores_non_list():
    from app.services import ai_service

    payload = _receipt_payload()
    payload["uncertain_fields"] = "total"

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.uncertain_fields == []


# --- 抽取層：解析與金額補齊 ------------------------------------------------


def test_parse_receipt_basic(monkeypatch):
    from app.services import ai_service

    _gemini(monkeypatch, _receipt_payload())

    result = ai_service.parse_receipt_response(json.dumps(_receipt_payload()))

    assert result.merchant == "全聯福利中心"
    assert result.purchased_at == "2026-10-18"
    assert result.currency == "TWD"
    assert result.total == Decimal("1250.00")
    assert [item.name for item in result.items] == ["鮮乳", "衛生紙"]
    assert result.items[0].quantity == 2
    assert result.items[0].unit_price == Decimal("62.00")
    assert result.items[0].subtotal == Decimal("124.00")


def test_parse_receipt_derives_unit_price_from_subtotal(monkeypatch):
    """單價缺、小計有 → 單價＝小計／數量（2 位四捨五入）。"""
    from app.services import ai_service

    payload = _receipt_payload(
        items=[{"name": "雞蛋", "quantity": 3, "unit_price": None, "subtotal": "100.00"}]
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.items[0].unit_price == Decimal("33.33")
    assert result.items[0].subtotal == Decimal("100.00")


def test_parse_receipt_derives_subtotal_from_unit_price(monkeypatch):
    """小計缺、單價有 → 小計＝單價×數量。"""
    from app.services import ai_service

    payload = _receipt_payload(
        items=[{"name": "咖啡豆", "quantity": 2, "unit_price": "350.00", "subtotal": None}]
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.items[0].subtotal == Decimal("700.00")


def test_parse_receipt_keeps_both_null_when_missing():
    """單價與小計皆缺 → 皆為 None（接受時成本留空，不阻擋）。"""
    from app.services import ai_service

    payload = _receipt_payload(
        items=[{"name": "贈品", "quantity": 1, "unit_price": None, "subtotal": None}]
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.items[0].unit_price is None
    assert result.items[0].subtotal is None


def test_parse_receipt_keeps_inconsistent_values():
    """兩者都有但不一致 → 保留原值，不覆寫。"""
    from app.services import ai_service

    payload = _receipt_payload(
        items=[{"name": "特價品", "quantity": 2, "unit_price": "50.00", "subtotal": "90.00"}]
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.items[0].unit_price == Decimal("50.00")
    assert result.items[0].subtotal == Decimal("90.00")


def test_parse_receipt_invalid_date_becomes_null():
    """`purchased_at` 非 ISO → null（單一欄位壞掉不整批失敗）。"""
    from app.services import ai_service

    payload = _receipt_payload()
    payload["purchased_at"] = "10月18日"

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.purchased_at is None


def test_parse_receipt_rejects_non_json():
    from app.services import ai_service

    with pytest.raises(ai_service.AiUpstreamError):
        ai_service.parse_receipt_response("not json at all")


def test_parse_receipt_rejects_empty_items():
    from app.services import ai_service

    with pytest.raises(ai_service.AiUpstreamError):
        ai_service.parse_receipt_response(json.dumps(_receipt_payload(items=[])))


def test_parse_receipt_skips_unnamed_items():
    """無名稱的列直接略過（不可建立草稿）。"""
    from app.services import ai_service

    payload = _receipt_payload(
        items=[
            {"name": "  ", "quantity": 1, "unit_price": "10.00", "subtotal": "10.00"},
            {"name": "鮮乳", "quantity": 1, "unit_price": "62.00", "subtotal": "62.00"},
        ]
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert [item.name for item in result.items] == ["鮮乳"]


def test_parse_receipt_defaults_quantity_to_one():
    from app.services import ai_service

    payload = _receipt_payload(
        items=[{"name": "麵包", "quantity": None, "unit_price": "45.00", "subtotal": "45.00"}]
    )

    result = ai_service.parse_receipt_response(json.dumps(payload))

    assert result.items[0].quantity == 1


def test_parse_receipt_clamps_item_limit():
    """品項上限 50：超出截斷（呼叫端回報 truncated）。"""
    from app.services import ai_service

    items = [
        {"name": f"品項{i}", "quantity": 1, "unit_price": "1.00", "subtotal": "1.00"}
        for i in range(55)
    ]

    result = ai_service.parse_receipt_response(
        json.dumps(_receipt_payload(items=items))
    )

    assert len(result.items) == 50


def test_call_gemini_receipt_sends_all_pages(monkeypatch, tmp_path):
    """多頁一次送出：單一請求、每頁一個 Part。"""
    from app.services import ai_service

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from app.config import get_settings

    get_settings.cache_clear()
    fake_client = _gemini(monkeypatch, _receipt_payload())

    pages = []
    for index in range(2):
        path = tmp_path / f"page{index}.png"
        path.write_bytes(_tiny_png())
        pages.append((path, "image/png"))

    import asyncio

    result = asyncio.run(ai_service.call_gemini_receipt(pages))

    assert len(result.items) == 2
    assert fake_client.models.generate_content.call_count == 1
    contents = fake_client.models.generate_content.call_args.kwargs["contents"]
    # prompt ＋ 2 頁
    assert len(contents) == 3


def test_call_gemini_receipt_upstream_error(monkeypatch, tmp_path):
    from app.services import ai_service

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from app.config import get_settings

    get_settings.cache_clear()
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)

    path = tmp_path / "page.png"
    path.write_bytes(_tiny_png())

    import asyncio

    with pytest.raises(ai_service.AiUpstreamError):
        asyncio.run(ai_service.call_gemini_receipt([(path, "image/png")]))


# --- 端點：POST /api/ai/receipts --------------------------------------------


async def _upload(client, headers: dict, name: str = "receipt.png") -> str:
    files = {"file": (name, _tiny_png(), "image/png")}
    r = await client.post("/api/images", headers=headers, files=files)
    assert r.status_code == 201
    return r.json()["id"]


async def _login(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _enable_ai(monkeypatch, payload: dict):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from app.config import get_settings

    get_settings.cache_clear()
    return _gemini(monkeypatch, payload)


async def test_create_receipt_creates_ready_item_drafts(client, auth, monkeypatch):
    await _enable_ai(monkeypatch, _receipt_payload())
    page1 = await _upload(client, auth, "page1.png")
    page2 = await _upload(client, auth, "page2.png")

    r = await client.post(
        "/api/ai/receipts", headers=auth, json={"image_ids": [page1, page2]}
    )

    assert r.status_code == 201
    body = r.json()
    assert body["truncated"] is False
    receipt_id = body["receipt_id"]
    assert len(body["created"]) == 2

    first, second = body["created"]
    # 同組、皆 ready、皆為收據來源、共用群組鍵
    assert {first["receipt_id"], second["receipt_id"]} == {receipt_id}
    assert [d["source"] for d in body["created"]] == ["receipt", "receipt"]
    assert [d["status"] for d in body["created"]] == ["ready", "ready"]
    # 卡片縮圖用第一頁
    assert first["image_id"] == page1
    assert first["processed_at"] is None

    # 依收據行序回傳
    assert [d["payload"]["receipt_item"]["index"] for d in body["created"]] == [0, 1]
    assert first["payload"]["ai"]["name"] == "鮮乳"
    assert first["payload"]["receipt_item"]["quantity"] == 2
    assert first["payload"]["receipt_item"]["unit_price"] == "62.00"
    assert first["payload"]["receipt"]["merchant"] == "全聯福利中心"
    assert first["payload"]["receipt"]["page_count"] == 2
    assert first["payload"]["receipt"]["item_total"] == "323.00"
    assert first["payload"]["receipt"]["discrepancy"] == "927.00"
    assert first["payload"]["history"] == {
        "category": None,
        "location": None,
        "tags": [],
    }


async def test_create_receipt_uses_history_rules(client, auth, monkeypatch):
    """分類建議沿用 Phase 32 歷史規則（批次化）。"""
    await _enable_ai(monkeypatch, _receipt_payload())
    category = (
        await client.post(
            "/api/categories", headers=auth, json={"name": "食品"}
        )
    ).json()
    await client.post(
        "/api/items",
        headers=auth,
        json={"name": "鮮乳", "quantity": 1, "category_id": category["id"]},
    )
    page = await _upload(client, auth)

    r = await client.post("/api/ai/receipts", headers=auth, json={"image_ids": [page]})

    assert r.status_code == 201
    first = r.json()["created"][0]
    assert first["payload"]["history"]["category"]["id"] == category["id"]
    assert first["payload"]["history"]["category"]["name"] == "食品"


async def test_create_receipt_requires_api_key(client, auth):
    page = await _upload(client, auth)

    r = await client.post("/api/ai/receipts", headers=auth, json={"image_ids": [page]})

    assert r.status_code == 503
    assert r.json()["detail"] == "ai_disabled"


async def test_create_receipt_quota_exhausted_creates_nothing(
    client, auth, monkeypatch, db_session
):
    from sqlalchemy import select

    from app.models.ai_draft import AiDraftItem

    await _enable_ai(monkeypatch, _receipt_payload())
    monkeypatch.setenv("AI_DAILY_QUOTA", "0")
    from app.config import get_settings

    get_settings.cache_clear()
    # 0 表示無限制，改用 1 次配額：先耗盡
    monkeypatch.setenv("AI_DAILY_QUOTA", "1")
    get_settings.cache_clear()
    page = await _upload(client, auth)
    first = await client.post(
        "/api/ai/receipts", headers=auth, json={"image_ids": [page]}
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/ai/receipts", headers=auth, json={"image_ids": [page]}
    )
    assert second.status_code == 429
    assert second.json()["detail"] == "quota_exhausted"

    rows = (await db_session.execute(select(AiDraftItem))).scalars().all()
    # 只有第一次成功的 2 筆
    assert len(rows) == 2


async def test_create_receipt_counts_once_per_receipt(client, auth, monkeypatch):
    """多頁只扣 1 次配額。"""
    await _enable_ai(monkeypatch, _receipt_payload())
    monkeypatch.setenv("AI_DAILY_QUOTA", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    page1 = await _upload(client, auth, "a.png")
    page2 = await _upload(client, auth, "b.png")

    r = await client.post(
        "/api/ai/receipts", headers=auth, json={"image_ids": [page1, page2]}
    )

    assert r.status_code == 201


async def test_create_receipt_upstream_error(client, auth, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from app.config import get_settings

    get_settings.cache_clear()
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)
    page = await _upload(client, auth)

    r = await client.post("/api/ai/receipts", headers=auth, json={"image_ids": [page]})

    assert r.status_code == 502
    assert r.json()["detail"] == "upstream_error"


async def test_create_receipt_no_items(client, auth, monkeypatch):
    await _enable_ai(monkeypatch, _receipt_payload(items=[]))
    page = await _upload(client, auth)

    r = await client.post("/api/ai/receipts", headers=auth, json={"image_ids": [page]})

    assert r.status_code == 422
    assert r.json()["detail"] == "no_items"


async def test_create_receipt_image_not_found(client, auth, monkeypatch):
    await _enable_ai(monkeypatch, _receipt_payload())

    r = await client.post(
        "/api/ai/receipts",
        headers=auth,
        json={"image_ids": ["00000000-0000-0000-0000-000000000000"]},
    )

    assert r.status_code == 404


async def test_create_receipt_rejects_too_many_pages(client, auth, monkeypatch):
    await _enable_ai(monkeypatch, _receipt_payload())

    r = await client.post(
        "/api/ai/receipts",
        headers=auth,
        json={"image_ids": ["00000000-0000-0000-0000-000000000000"] * 11},
    )

    assert r.status_code == 422


async def test_create_receipt_truncates_items(client, auth, monkeypatch):
    items = [
        {"name": f"品項{i}", "quantity": 1, "unit_price": "1.00", "subtotal": "1.00"}
        for i in range(55)
    ]
    await _enable_ai(monkeypatch, _receipt_payload(items=items))
    page = await _upload(client, auth)

    r = await client.post("/api/ai/receipts", headers=auth, json={"image_ids": [page]})

    assert r.status_code == 201
    body = r.json()
    assert body["truncated"] is True
    assert len(body["created"]) == 50


async def test_create_receipt_other_users_image_is_404(client, monkeypatch):
    await _enable_ai(monkeypatch, _receipt_payload())
    owner = await _login(client, "rc_owner")
    other = await _login(client, "rc_other")
    page = await _upload(client, owner)

    r = await client.post("/api/ai/receipts", headers=other, json={"image_ids": [page]})

    assert r.status_code == 404


async def test_create_receipt_viewer_forbidden(client, monkeypatch):
    await _enable_ai(monkeypatch, _receipt_payload())
    owner = await _login(client, "rc_v_owner")
    viewer = await _login(client, "rc_viewer")
    gid = (
        await client.post("/api/groups", headers=owner, json={"name": "g-rc"})
    ).json()["id"]
    assert (
        await client.post(
            f"/api/groups/{gid}/members",
            headers=owner,
            json={"username": "rc_viewer", "role": "viewer"},
        )
    ).status_code == 201
    page = await _upload(client, owner)

    r = await client.post("/api/ai/receipts", headers=viewer, json={"image_ids": [page]})

    assert r.status_code == 403


async def test_create_receipt_does_not_block_photo_drafts(client, auth, monkeypatch):
    """收據照片不誤擋一般照片草稿（去重限定 batch_photo）。"""
    await _enable_ai(monkeypatch, _receipt_payload())
    page = await _upload(client, auth)

    receipt = await client.post(
        "/api/ai/receipts", headers=auth, json={"image_ids": [page]}
    )
    assert receipt.status_code == 201

    photo = await client.post("/api/ai/drafts", headers=auth, json={"image_ids": [page]})
    assert photo.status_code == 201
    assert len(photo.json()["created"]) == 1
