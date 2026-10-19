from __future__ import annotations

import struct
import uuid
import zlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.ai_draft import AiDraftItem


def _tiny_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        import zlib as z

        return (
            struct.pack(">I", len(data))
            + tag
            + data
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


async def _login(client, username: str) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _member_auth(client, name: str, role: str) -> dict:
    owner = await _login(client, f"{name}_owner")
    member = await _login(client, name)
    gid = (
        await client.post("/api/groups", headers=owner, json={"name": f"g-{name}"})
    ).json()["id"]
    r = await client.post(
        f"/api/groups/{gid}/members",
        headers=owner,
        json={"username": name, "role": role},
    )
    assert r.status_code == 201
    return member


async def _upload(client, headers: dict) -> str:
    files = {"file": ("x.png", _tiny_png(), "image/png")}
    r = await client.post("/api/images", headers=headers, files=files)
    assert r.status_code == 201
    return r.json()["id"]


async def test_create_drafts_creates_pending_rows(client):
    auth = await _login(client, "drafts_a")
    first = await _upload(client, auth)
    second = await _upload(client, auth)

    r = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [first, second]}
    )

    assert r.status_code == 201
    body = r.json()
    assert body["skipped_image_ids"] == []
    assert [d["image_id"] for d in body["created"]] == [first, second]
    for draft in body["created"]:
        assert draft["source"] == "batch_photo"
        assert draft["status"] == "pending"
        assert draft["error_code"] is None
        assert draft["item_id"] is None
        assert draft["processed_at"] is None
        assert draft["payload"] == {
            "version": 1,
            "ai": None,
            "history": {"category": None, "location": None, "tags": []},
            "receipt": None,
            "receipt_item": None,
        }


async def test_create_drafts_skips_existing_active_drafts(client):
    auth = await _login(client, "drafts_b")
    image_id = await _upload(client, auth)

    first = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [image_id]}
    )
    assert len(first.json()["created"]) == 1

    second = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [image_id]}
    )
    assert second.status_code == 201
    assert second.json()["created"] == []
    assert second.json()["skipped_image_ids"] == [image_id]


async def test_create_drafts_allows_recreate_after_failure(client, db_session):
    auth = await _login(client, "drafts_c")
    image_id = await _upload(client, auth)
    created = (
        await client.post("/api/ai/drafts", headers=auth, json={"image_ids": [image_id]})
    ).json()["created"][0]

    draft = (
        await db_session.execute(
            select(AiDraftItem).where(AiDraftItem.id == uuid.UUID(created["id"]))
        )
    ).scalar_one()
    draft.status = "failed"
    draft.error_code = "upstream_error"
    await db_session.commit()

    retry = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [image_id]}
    )
    assert retry.status_code == 201
    assert len(retry.json()["created"]) == 1


async def test_create_drafts_requires_visible_images(client):
    auth = await _login(client, "drafts_d")
    other = await _login(client, "drafts_d_other")
    other_image = await _upload(client, other)

    missing = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [str(uuid.uuid4())]}
    )
    assert missing.status_code == 404

    foreign = await client.post(
        "/api/ai/drafts", headers=auth, json={"image_ids": [other_image]}
    )
    assert foreign.status_code == 404


async def test_create_drafts_validation(client):
    auth = await _login(client, "drafts_e")
    image_id = await _upload(client, auth)

    empty = await client.post("/api/ai/drafts", headers=auth, json={"image_ids": []})
    assert empty.status_code == 422

    too_many = await client.post(
        "/api/ai/drafts",
        headers=auth,
        json={"image_ids": [image_id] * 11},
    )
    assert too_many.status_code == 422

    extra = await client.post(
        "/api/ai/drafts",
        headers=auth,
        json={"image_ids": [image_id], "source": "receipt"},
    )
    assert extra.status_code == 422


async def test_list_drafts_defaults_to_active_with_counts(client, db_session):
    auth = await _login(client, "drafts_f")
    first = await _upload(client, auth)
    second = await _upload(client, auth)
    created = (
        await client.post(
            "/api/ai/drafts", headers=auth, json={"image_ids": [first, second]}
        )
    ).json()["created"]

    draft = (
        await db_session.execute(
            select(AiDraftItem).where(AiDraftItem.id == uuid.UUID(created[1]["id"]))
        )
    ).scalar_one()
    draft.status = "discarded"
    await db_session.commit()

    r = await client.get("/api/ai/drafts", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert [d["id"] for d in body["items"]] == [created[0]["id"]]
    assert body["total"] == 1
    assert body["counts"] == {
        "pending": 1,
        "processing": 0,
        "ready": 0,
        "failed": 0,
        "accepted": 0,
        "discarded": 1,
    }


async def test_list_drafts_status_filter(client, db_session):
    auth = await _login(client, "drafts_g")
    image_id = await _upload(client, auth)
    created = (
        await client.post("/api/ai/drafts", headers=auth, json={"image_ids": [image_id]})
    ).json()["created"][0]

    draft = (
        await db_session.execute(
            select(AiDraftItem).where(AiDraftItem.id == uuid.UUID(created["id"]))
        )
    ).scalar_one()
    draft.status = "accepted"
    await db_session.commit()

    pending = await client.get("/api/ai/drafts?status=pending", headers=auth)
    assert pending.json()["items"] == []

    accepted = await client.get("/api/ai/drafts?status=accepted", headers=auth)
    assert [d["id"] for d in accepted.json()["items"]] == [created["id"]]

    invalid = await client.get("/api/ai/drafts?status=bogus", headers=auth)
    assert invalid.status_code == 422


async def test_list_drafts_only_own(client):
    auth = await _login(client, "drafts_h")
    other = await _login(client, "drafts_h_other")
    image_id = await _upload(client, auth)
    await client.post("/api/ai/drafts", headers=auth, json={"image_ids": [image_id]})

    r = await client.get("/api/ai/drafts", headers=other)
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


async def test_list_drafts_newest_first_with_pagination(client, db_session):
    auth = await _login(client, "drafts_i")
    ids = [await _upload(client, auth) for _ in range(3)]
    (
        await client.post("/api/ai/drafts", headers=auth, json={"image_ids": ids})
    ).json()["created"]

    rows = (
        await db_session.execute(
            select(AiDraftItem).order_by(AiDraftItem.created_at, AiDraftItem.id)
        )
    ).scalars().all()
    base = datetime(2026, 10, 19, 3, 0, tzinfo=UTC)
    for index, row in enumerate(rows):
        row.created_at = base + timedelta(minutes=index)
    await db_session.commit()
    expected = [str(row.id) for row in rows][::-1]

    page = await client.get("/api/ai/drafts?limit=2", headers=auth)
    body = page.json()
    assert [d["id"] for d in body["items"]] == expected[:2]
    assert body["total"] == 3

    offset = await client.get("/api/ai/drafts?limit=2&offset=2", headers=auth)
    assert [d["id"] for d in offset.json()["items"]] == expected[2:]


async def test_viewer_blocked_from_create_but_can_read(client):
    viewer = await _member_auth(client, "drafts_viewer", "viewer")

    blocked = await client.post(
        "/api/ai/drafts", headers=viewer, json={"image_ids": [str(uuid.uuid4())]}
    )
    assert blocked.status_code == 403

    readable = await client.get("/api/ai/drafts", headers=viewer)
    assert readable.status_code == 200
    assert readable.json()["items"] == []
