from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

import pytest


def _tiny_png() -> bytes:
    """Return a 1x1 red PNG."""
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"  # filter byte + RGB red
    idat = zlib.compress(raw)
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(autouse=True)
def _isolated_media(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "img@t.io", "username": "img_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "img_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_upload_and_fetch(client, auth):
    png = _tiny_png()
    files = {"file": ("red.png", png, "image/png")}
    r = await client.post("/api/images", headers=auth, files=files)
    assert r.status_code == 201
    body = r.json()
    assert body["mime_type"] == "image/png"
    assert body["size_bytes"] == len(png)

    fetched = await client.get(f"/api/images/{body['id']}", headers=auth)
    assert fetched.status_code == 200
    assert fetched.content == png


async def test_upload_reject_bad_mime(client, auth):
    files = {"file": ("bad.txt", b"hi", "text/plain")}
    r = await client.post("/api/images", headers=auth, files=files)
    assert r.status_code == 415


async def test_delete_image(client, auth):
    png = _tiny_png()
    files = {"file": ("x.png", png, "image/png")}
    body = (await client.post("/api/images", headers=auth, files=files)).json()
    r = await client.delete(f"/api/images/{body['id']}", headers=auth)
    assert r.status_code == 204


async def test_cross_owner_cannot_fetch(client, auth):
    png = _tiny_png()
    files = {"file": ("x.png", png, "image/png")}
    body = (await client.post("/api/images", headers=auth, files=files)).json()
    await client.post("/api/auth/register", json={"email": "o@t.io", "username": "o_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "o_user", "password": "secret1234"})
    other_h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    fetched = await client.get(f"/api/images/{body['id']}", headers=other_h)
    assert fetched.status_code == 404
