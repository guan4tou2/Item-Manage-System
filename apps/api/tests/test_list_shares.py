"""清單分享的公開邊界與憑證生命週期。"""

import hashlib
import json
import logging
import re
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.db.base import _utcnow


async def login(client, name="share_owner"):
    await client.post(
        "/api/auth/register",
        json={
            "email": f"{name}@t.io",
            "username": name,
            "password": "secret1234",
        },
    )
    r = await client.post(
        "/api/auth/login", json={"username": name, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def owned(client):
    auth = await login(client)
    r = await client.post(
        "/api/lists",
        headers=auth,
        json={
            "kind": "shopping",
            "title": "旅行用品",
            "budget": "5000",
            "description": "帶去露營",
            "start_date": "2026-11-15",
            "end_date": "2026-11-16",
        },
    )
    lid = r.json()["id"]
    for name, link in [
        ("牙刷", "javascript:alert(1)"),
        ("帳篷", "https://example.com"),
    ]:
        await client.post(
            f"/api/lists/{lid}/entries",
            headers=auth,
            json={
                "name": name,
                "price": "1200",
                "link": link,
                "quantity": 2,
            },
        )
    return auth, lid


async def create(client, owned, days=7, prices=False):
    auth, lid = owned
    return await client.post(
        f"/api/lists/{lid}/shares",
        headers=auth,
        json={
            "expires_in_days": days,
            "show_prices": prices,
        },
    )


async def public(client, token):
    return await client.get("/api/public/list", headers={"X-Share-Token": token})


async def test_public_whitelist(client, owned):
    r = await create(client, owned)
    assert r.status_code == 201
    response = await public(client, r.json()["token"])
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "kind",
        "title",
        "description",
        "start_date",
        "end_date",
        "entries",
    }
    assert [e["name"] for e in body["entries"]] == ["牙刷", "帳篷"]
    assert set(body["entries"][0]) == {"name", "quantity", "note", "link", "is_done"}
    assert body["entries"][0]["link"] is None
    assert body["entries"][1]["link"] == "https://example.com"
    serialized = response.text
    for secret in [
        "share_owner",
        "share_owner@t.io",
        "budget",
        "price",
        "owner_id",
        "created_at",
        "updated_at",
    ]:
        assert secret not in serialized
    assert not re.search(
        r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", serialized
    )


@pytest.mark.parametrize("days", [1, 7, 30, None])
async def test_expiry_and_one_time_storage(client, owned, db_session, days):
    from app.models.list_share import ListShare

    before = _utcnow()
    r = await create(client, owned, days)
    assert r.status_code == 201
    data = r.json()
    token = data["token"]
    assert len(token) == 43
    assert data["token_prefix"] == token[:6]
    row = (await db_session.execute(select(ListShare))).scalar_one()
    assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in json.dumps({k: str(v) for k, v in vars(row).items()})
    if days is None:
        assert row.expires_at is None
    else:
        delta = row.expires_at.replace(tzinfo=before.tzinfo) - before
        assert timedelta(days=days) <= delta < timedelta(days=days, seconds=5)
    auth, lid = owned
    listed = await client.get(f"/api/lists/{lid}/shares", headers=auth)
    assert token not in listed.text and row.token_hash not in listed.text
    assert "token" not in listed.json()[0]
    assert (await public(client, token)).status_code == 200
    row.expires_at = _utcnow() - timedelta(seconds=1)
    await db_session.commit()
    expired = await public(client, token)
    assert expired.status_code == 404
    assert expired.json() == (await public(client, "x" * 43)).json()
    assert (await client.get(f"/api/lists/{lid}/shares", headers=auth)).json() == []
    db_session.expire_all()
    assert (await db_session.execute(select(ListShare))).scalar_one_or_none() is None


async def test_prices_opt_in_and_single_list(client, owned):
    auth, _ = owned
    await client.put(
        "/api/users/me/preferences", headers=auth, json={"currency": "USD"}
    )
    await client.post(
        "/api/lists", headers=auth, json={"kind": "generic", "title": "秘密清單"}
    )
    r = await create(client, owned, prices=True)
    response = await public(client, r.json()["token"])
    assert response.json()["budget"] == "5000.00"
    assert response.json()["entries"][0]["price"] == "1200.00"
    assert response.json()["currency"] == "USD"
    assert "秘密清單" not in response.text
    for key in ["owner_id", "list_id", "created_at", "updated_at", "share_owner"]:
        assert key not in response.text
    assert not re.search(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", response.text)


async def test_revoke_and_delete_list(client, owned):
    auth, lid = owned
    data = (await create(client, owned)).json()
    assert (
        await client.delete(f"/api/lists/{lid}/shares/{data['id']}", headers=auth)
    ).status_code == 204
    assert (await public(client, data["token"])).status_code == 404
    data = (await create(client, owned)).json()
    assert (await client.delete(f"/api/lists/{lid}", headers=auth)).status_code == 204
    assert (await public(client, data["token"])).status_code == 404


async def test_limit_excludes_expired(client, owned, db_session):
    from app.models.list_share import ListShare

    for _ in range(5):
        assert (await create(client, owned)).status_code == 201
    assert (await create(client, owned)).status_code == 409
    row = (await db_session.execute(select(ListShare))).scalars().first()
    row.expires_at = _utcnow() - timedelta(seconds=1)
    await db_session.commit()
    assert (await create(client, owned)).status_code == 201


async def test_ownership_and_viewer_guard(client, owned):
    auth, lid = owned
    other = await login(client, "share_other")
    data = (await create(client, owned)).json()
    for method, path, body in [
        ("GET", f"/api/lists/{lid}/shares", None),
        ("POST", f"/api/lists/{lid}/shares", {"expires_in_days": 7}),
        ("DELETE", f"/api/lists/{lid}/shares/{data['id']}", None),
    ]:
        assert (
            await client.request(method, path, headers=other, json=body)
        ).status_code == 404
        assert (await client.request(method, path, json=body)).status_code == 401
    # 清單擁有者成為其他群組的 viewer，讀取仍允許，寫入受 guard 阻擋。
    gid = (
        await client.post("/api/groups", headers=other, json={"name": "群組"})
    ).json()["id"]
    await client.post(
        f"/api/groups/{gid}/members",
        headers=other,
        json={"username": "share_owner", "role": "viewer"},
    )
    assert (
        await client.get(f"/api/lists/{lid}/shares", headers=auth)
    ).status_code == 200
    assert (await create(client, owned)).status_code == 403
    assert (
        await client.delete(f"/api/lists/{lid}/shares/{data['id']}", headers=auth)
    ).status_code == 403


@pytest.mark.parametrize("token", [None, "", "wrong", "x" * 43])
async def test_invalid_and_headers(client, token):
    headers = {"X-Share-Token": token} if token is not None else {}
    r = await client.get("/api/public/list", headers=headers)
    assert r.status_code == 404
    assert r.json() == {"detail": "share not found"}
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert r.headers["referrer-policy"] == "no-referrer"


async def test_access_count_headers_and_fail_soft(
    client, owned, db_session, monkeypatch
):
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.dml import Update

    from app.models.list_share import ListShare

    data = (await create(client, owned)).json()
    for _ in range(2):
        r = await public(client, data["token"])
        assert r.status_code == 200
        assert r.headers["cache-control"] == "no-store"
        assert r.headers["x-robots-tag"] == "noindex, nofollow"
        assert r.headers["referrer-policy"] == "no-referrer"
    row = await db_session.get(ListShare, UUID(data["id"]))
    assert row.access_count == 2 and row.last_accessed_at is not None
    execute = AsyncSession.execute

    async def fail_update(self, statement, *args, **kwargs):
        if isinstance(statement, Update) and statement.table.name == "list_shares":
            raise RuntimeError("計數寫入失敗")
        return await execute(self, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, "execute", fail_update)
    assert (await public(client, data["token"])).status_code == 200
    await db_session.refresh(row)
    assert row.access_count == 2


async def test_audit_and_access_log_no_credentials(client, owned, db_session, caplog):
    from app.models.favorite_audit_token import AuditLog

    caplog.set_level(logging.INFO)
    data = (await create(client, owned)).json()
    before = (await db_session.execute(select(AuditLog.id))).all()
    await public(client, data["token"])
    assert (await db_session.execute(select(AuditLog.id))).all() == before
    auth, lid = owned
    await client.delete(f"/api/lists/{lid}/shares/{data['id']}", headers=auth)
    rows = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.action.like("list.share_%"),
                )
            )
        )
        .scalars()
        .all()
    )
    assert {row.action for row in rows} == {"list.share_created", "list.share_revoked"}
    for row in rows:
        assert set(row.meta) == {"list_id", "expires_at", "show_prices", "token_prefix"}
        assert row.meta["token_prefix"] == data["token"][:6]
        serialized = json.dumps(
            {
                column.name: getattr(row, column.name)
                for column in AuditLog.__table__.columns
            },
            default=str,
        )
        assert data["token"] not in serialized
        assert hashlib.sha256(data["token"].encode()).hexdigest() not in serialized
    assert data["token"] not in caplog.text
    access = [r for r in caplog.records if r.name == "ims.access"]
    assert any(r.path == "/api/public/list" for r in access)
    assert data["token"] not in str([vars(r) for r in access])


async def test_backup_excludes_credentials(client, owned, db_session):
    from app.models.list_share import ListShare

    auth, _ = owned
    data = (await create(client, owned)).json()
    r = await client.get("/api/backup/export", headers=auth)
    assert r.status_code == 200
    for secret in [
        "list_shares",
        "token_hash",
        "token_prefix",
        data["token"],
        hashlib.sha256(data["token"].encode()).hexdigest(),
    ]:
        assert secret not in r.text
    backup = r.json()
    row = await db_session.get(ListShare, UUID(data["id"]))
    forged = {
        column.name: getattr(row, column.name) for column in ListShare.__table__.columns
    }
    forged.update(
        id=uuid4(),
        token_hash=hashlib.sha256(("b" * 43).encode()).hexdigest(),
        token_prefix="bbbbbb",
    )
    backup["list_shares"] = [forged]
    r = await client.post(
        "/api/backup/import",
        headers=auth,
        files={
            "file": ("backup.json", json.dumps(backup, default=str), "application/json")
        },
    )
    assert r.status_code == 200
    assert (await public(client, "b" * 43)).status_code == 404
    rows = (await db_session.execute(select(ListShare))).scalars().all()
    assert len(rows) == 1
    assert str(rows[0].id) == data["id"]
    assert (await client.get(f"/api/lists/{owned[1]}/shares", headers=auth)).json()[0][
        "id"
    ] == data["id"]


@pytest.mark.parametrize("body", [{}, {"expires_in_days": 2}, {"expires_in_days": -1}])
async def test_expiry_required_and_validated(client, owned, body):
    auth, lid = owned
    r = await client.post(f"/api/lists/{lid}/shares", headers=auth, json=body)
    assert r.status_code == 422


@pytest.mark.parametrize("target", ["list", "owner"])
async def test_foreign_key_cascade(client, owned, db_session, target):
    from sqlalchemy import delete, text

    from app.models.list import List
    from app.models.list_share import ListShare
    from app.models.user import User

    data = (await create(client, owned)).json()
    row = await db_session.get(ListShare, UUID(data["id"]))
    owner_id = row.owner_id
    await db_session.commit()
    # SQLite 測試引擎預設不啟用 FK，這裡啟用以實際驗證 CASCADE。
    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    if target == "list":
        await db_session.execute(delete(List).where(List.id == UUID(owned[1])))
    else:
        await db_session.execute(delete(User).where(User.id == owner_id))
    await db_session.commit()
    assert (await db_session.execute(select(ListShare.id))).all() == []
    assert (await public(client, data["token"])).status_code == 404


async def test_count_commit_failure_is_soft(client, owned, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    data = (await create(client, owned)).json()

    async def failed_commit(self):
        raise RuntimeError("計數提交失敗")

    monkeypatch.setattr(AsyncSession, "commit", failed_commit)
    response = await public(client, data["token"])
    assert response.status_code == 200
    assert response.json()["title"] == "旅行用品"


@pytest.mark.parametrize(
    "link",
    [
        "javascript:alert(1)",
        "data:text/html,x",
        "//example.com",
        "/items/secret",
        "ftp://example.com",
    ],
)
async def test_unsafe_links_are_null(client, owned, link):
    auth, lid = owned
    await client.post(
        f"/api/lists/{lid}/entries", headers=auth, json={"name": "連結", "link": link}
    )
    data = (await create(client, owned)).json()
    body = (await public(client, data["token"])).json()
    assert body["entries"][-1]["link"] is None
    assert json.dumps(link) not in json.dumps(body)
