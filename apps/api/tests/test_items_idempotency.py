"""離線新增：交易、重送與副作用的回歸測試。"""
import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base, _utcnow
from app.db.session import get_db
from app.main import create_app
from app.models.favorite_audit_token import AuditLog
from app.models.idempotency_key import IdempotencyKey
from app.models.item import Item
from app.services import items_service, webhooks_service


async def login(client, name="offline_user"):
    response = await client.post("/api/auth/register", json={
        "email": f"{name}@t.io", "username": name, "password": "secret1234",
    })
    assert response.status_code == 201
    response = await client.post("/api/auth/login", json={
        "username": name, "password": "secret1234",
    })
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def headers(client):
    return {**await login(client), "Idempotency-Key": str(uuid4())}


async def test_replay_same_item_without_side_effects(client, headers, db_session, monkeypatch):
    dispatch = AsyncMock()
    monkeypatch.setattr(webhooks_service, "dispatch", dispatch)
    first = await client.post("/api/items", headers=headers, json={"name": "離線物品"})
    assert first.status_code == 201
    audit_count = await db_session.scalar(select(func.count()).select_from(AuditLog))
    # key 命中時不重新驗證已經失效的分類，也不採用新的 payload。
    second = await client.post("/api/items", headers=headers, json={"name": "不同名稱", "category_id": 9999})
    assert second.status_code == 200
    assert second.json() == first.json()
    assert await db_session.scalar(select(func.count()).select_from(Item)) == 1
    assert await db_session.scalar(select(func.count()).select_from(IdempotencyKey)) == 1
    assert await db_session.scalar(select(func.count()).select_from(AuditLog)) == audit_count
    dispatch.assert_awaited_once()


async def test_same_key_different_users(client, headers):
    other = {**await login(client, "offline_other"), "Idempotency-Key": headers["Idempotency-Key"]}
    a = await client.post("/api/items", headers=headers, json={"name": "甲"})
    b = await client.post("/api/items", headers=other, json={"name": "乙"})
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] != b.json()["id"]


async def test_invalid_key(client, headers):
    headers["Idempotency-Key"] = "not-a-uuid"
    response = await client.post("/api/items", headers=headers, json={"name": "物品"})
    assert response.status_code == 422


async def test_deleted_item_is_gone(client, headers):
    first = await client.post("/api/items", headers=headers, json={"name": "物品"})
    deleted = await client.delete(f"/api/items/{first.json()['id']}", headers=headers)
    assert deleted.status_code == 204
    replay = await client.post("/api/items", headers=headers, json={"name": "物品"})
    assert replay.status_code == 410
    assert replay.json() == {"code": "idempotent_item_deleted"}


async def test_expired_key_is_cleaned_and_becomes_new_request(client, headers, db_session):
    first = await client.post("/api/items", headers=headers, json={"name": "物品"})
    await db_session.execute(update(IdempotencyKey).values(created_at=_utcnow() - timedelta(days=8)))
    await db_session.commit()
    second = await client.post("/api/items", headers=headers, json={"name": "物品"})
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]
    assert await db_session.scalar(select(func.count()).select_from(IdempotencyKey)) == 1


async def test_without_key_still_creates_each_time(client, headers, db_session):
    del headers["Idempotency-Key"]
    a = await client.post("/api/items", headers=headers, json={"name": "物品"})
    b = await client.post("/api/items", headers=headers, json={"name": "物品"})
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] != b.json()["id"]
    assert await db_session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0


async def test_viewer_forbidden(client):
    owner = await login(client, "offline_owner")
    viewer = await login(client, "offline_viewer")
    group = (await client.post("/api/groups", headers=owner, json={"name": "家庭"})).json()
    added = await client.post(f"/api/groups/{group['id']}/members", headers=owner,
                              json={"username": "offline_viewer", "role": "viewer"})
    assert added.status_code == 201
    response = await client.post("/api/items", headers={**viewer, "Idempotency-Key": str(uuid4())},
                                 json={"name": "物品"})
    assert response.status_code == 403


async def test_failed_create_does_not_keep_key(client, headers, db_session):
    response = await client.post("/api/items", headers=headers, json={"name": "物品", "location_id": 9999})
    assert response.status_code == 422
    assert await db_session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0
    assert await db_session.scalar(select(func.count()).select_from(Item)) == 0


async def test_unique_conflict_rolls_back_item_and_replays(client, headers, db_session, monkeypatch):
    first = await client.post("/api/items", headers=headers, json={"name": "原物品"})
    original = items_service._idempotent_result
    calls = 0

    async def miss_then_hit(*args):
        nonlocal calls
        calls += 1
        return None if calls == 1 else await original(*args)

    monkeypatch.setattr(items_service, "_idempotent_result", miss_then_hit)
    dispatch = AsyncMock()
    monkeypatch.setattr(webhooks_service, "dispatch", dispatch)
    replay = await client.post("/api/items", headers=headers, json={"name": "競爭物品"})
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert await db_session.scalar(select(func.count()).select_from(Item)) == 1
    dispatch.assert_not_awaited()


async def test_parallel_replay_sqlite_file(tmp_path, monkeypatch):
    # 檔案 SQLite 使用真正的獨立連線，避免 :memory: 單一連線假並行。
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'parallel.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    async def db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = db
    dispatch = AsyncMock()
    monkeypatch.setattr(webhooks_service, "dispatch", dispatch)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {**await login(client), "Idempotency-Key": str(uuid4())}
            responses = await asyncio.gather(*[
                client.post("/api/items", headers=headers, json={"name": "同一物品", "tag_names": ["新標籤"]})
                for _ in range(4)
            ])
            assert sorted(r.status_code for r in responses) == [200, 200, 200, 201]
            assert len({r.json()["id"] for r in responses}) == 1
        async with maker() as session:
            assert await session.scalar(select(func.count()).select_from(Item)) == 1
            assert await session.scalar(select(func.count()).select_from(IdempotencyKey)) == 1
        dispatch.assert_awaited_once()
    finally:
        await engine.dispose()
