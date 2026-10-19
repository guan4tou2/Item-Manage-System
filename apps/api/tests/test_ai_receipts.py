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
