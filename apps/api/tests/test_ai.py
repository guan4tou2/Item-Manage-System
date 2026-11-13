from __future__ import annotations

import struct
import uuid
import zlib
from unittest.mock import MagicMock

import pytest


def _tiny_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    def chunk(tag: bytes, data: bytes) -> bytes:
        import zlib as z
        return (
            struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", z.crc32(tag + data) & 0xFFFFFFFF)
        )
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\x00\xff\x00"
    idat = zlib.compress(raw)
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(autouse=True)
def _media_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "ai@t.io", "username": "ai_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "ai_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_suggest_requires_api_key(client, auth):
    # GEMINI_API_KEY not set
    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()
    r = await client.post(
        "/api/ai/suggest-from-image", headers=auth, json={"image_id": img["id"]},
    )
    assert r.status_code == 503


async def test_suggest_with_mocked_gemini(client, auth, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from app.config import get_settings
    get_settings.cache_clear()

    # Mock the google.genai.Client
    fake_response = MagicMock()
    fake_response.text = '{"name":"咖啡杯","description":"陶瓷咖啡杯","category_suggestion":"廚房用品","tag_suggestions":["咖啡","陶瓷"]}'
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)

    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()
    r = await client.post(
        "/api/ai/suggest-from-image", headers=auth, json={"image_id": img["id"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "咖啡杯"
    assert body["category_suggestion"] == "廚房用品"
    assert "咖啡" in body["tag_suggestions"]


async def test_suggest_image_not_found(client, auth, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from app.config import get_settings
    get_settings.cache_clear()

    r = await client.post(
        "/api/ai/suggest-from-image", headers=auth,
        json={"image_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


def _mock_gemini(monkeypatch, response_text: str) -> MagicMock:
    fake_response = MagicMock()
    fake_response.text = response_text
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)
    return fake_client


async def test_suggest_quota_exhausted_returns_429(client, auth, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("AI_DAILY_QUOTA", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    fake_client = _mock_gemini(
        monkeypatch, '{"name":"咖啡杯","description":null,"category_suggestion":null,"tag_suggestions":[]}'
    )

    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()

    first = await client.post(
        "/api/ai/suggest-from-image", headers=auth, json={"image_id": img["id"]},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/ai/suggest-from-image", headers=auth, json={"image_id": img["id"]},
    )
    assert second.status_code == 429
    assert "quota" in second.json()["detail"]
    assert fake_client.models.generate_content.call_count == 1


async def test_suggest_upstream_failure_consumes_quota(client, auth, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("AI_DAILY_QUOTA", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    monkeypatch.setattr("google.genai.Client", lambda api_key: fake_client)

    files = {"file": ("x.png", _tiny_png(), "image/png")}
    img = (await client.post("/api/images", headers=auth, files=files)).json()

    failed = await client.post(
        "/api/ai/suggest-from-image", headers=auth, json={"image_id": img["id"]},
    )
    assert failed.status_code == 502

    # 失敗仍計次 → 已達每日上限
    blocked = await client.post(
        "/api/ai/suggest-from-image", headers=auth, json={"image_id": img["id"]},
    )
    assert blocked.status_code == 429
