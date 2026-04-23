from __future__ import annotations

import io
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

    import app.services.ai_service as ai_module
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
