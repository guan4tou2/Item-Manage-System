"""Phase 52：離線編輯／刪除的版本檢查與拒絕時的副作用。"""
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.favorite_audit_token import AuditLog
from app.models.item_history import ItemVersion, QuantityLog
from app.services import items_service, webhooks_service
from tests import test_items_routes, test_readonly_guard

auth_headers = test_items_routes.auth_headers
viewer_auth = test_readonly_guard.viewer_auth


def as_utc(value):
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


@pytest.fixture
async def item(client, auth_headers):
    response = await client.post('/api/items', headers=auth_headers, json={
        'name': '原物品', 'quantity': 3, 'cost': '12.30', 'tag_names': ['keep'],
    })
    assert response.status_code == 201
    return response.json()


async def write(client, method, item_id, headers):
    kwargs = {'json': {'name': '修改物品', 'quantity': 2, 'tag_names': ['changed']}} if method == 'PATCH' else {}
    return await client.request(method, f'/api/items/{item_id}', headers=headers, **kwargs)


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
async def test_without_header_preserves_behavior(client, auth_headers, item, method):
    response = await write(client, method, item['id'], auth_headers)
    assert response.status_code == (200 if method == 'PATCH' else 204)
    current = await client.get(f"/api/items/{item['id']}", headers=auth_headers)
    if method == 'PATCH':
        assert current.json()['name'] == '修改物品'
    else:
        assert current.status_code == 404


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
@pytest.mark.parametrize('wrapper', ['{}', '"{}"', 'W/"{}"', 'W/{}'])
@pytest.mark.parametrize('offset', [None, 0, 8])
async def test_matching_timestamp_accepted(client, auth_headers, item, method, wrapper, offset):
    timestamp = item['updated_at']
    if offset is not None:
        timestamp = as_utc(timestamp).astimezone(timezone(timedelta(hours=offset))).isoformat()
    response = await write(client, method, item['id'], {
        **auth_headers, 'If-Match': wrapper.format(timestamp),
    })
    assert response.status_code == (200 if method == 'PATCH' else 204)
    if method == 'PATCH':
        assert response.json()['name'] == '修改物品'
        assert as_utc(response.json()['updated_at']) > as_utc(item['updated_at'])
    else:
        assert (await client.get(f"/api/items/{item['id']}", headers=auth_headers)).status_code == 404


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
async def test_conflict_has_current_without_mutations(
    client, auth_headers, item, method, db_session, monkeypatch,
):
    # 一微秒的差異也必須拒絕；完整讀取結果涵蓋標籤、金額等序列化。
    current = (await client.get(f"/api/items/{item['id']}", headers=auth_headers)).json()
    models = [AuditLog, ItemVersion, QuantityLog]
    counts = [await db_session.scalar(select(func.count()).select_from(model)) for model in models]
    dispatch = AsyncMock()
    monkeypatch.setattr(webhooks_service, 'dispatch', dispatch)
    stale = (as_utc(item['updated_at']) - timedelta(microseconds=1)).isoformat()
    response = await write(client, method, item['id'], {**auth_headers, 'If-Match': stale})
    assert response.status_code == 412
    assert response.json() == {'detail': {'code': 'item_modified', 'current': current}}
    unchanged = await client.get(f"/api/items/{item['id']}", headers=auth_headers)
    assert unchanged.status_code == 200
    assert unchanged.json() == current
    for model, count in zip(models, counts, strict=True):
        assert await db_session.scalar(select(func.count()).select_from(model)) == count
    dispatch.assert_not_awaited()


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
@pytest.mark.parametrize('value', ['', 'not-a-date', '"unclosed', 'W/"bad"', '*'])
async def test_invalid_header_422(client, auth_headers, item, method, value, monkeypatch):
    dispatch = AsyncMock()
    monkeypatch.setattr(webhooks_service, 'dispatch', dispatch)
    before = (await client.get(f"/api/items/{item['id']}", headers=auth_headers)).json()
    response = await write(client, method, item['id'], {**auth_headers, 'If-Match': value})
    assert response.status_code == 422
    assert (await client.get(f"/api/items/{item['id']}", headers=auth_headers)).json() == before
    dispatch.assert_not_awaited()


@pytest.mark.parametrize('body', [{'tag_names': ['new']}, {'tag_names': ['keep']}, {}])
async def test_every_success_advances_timestamp(client, auth_headers, item, body, monkeypatch):
    # 時鐘沒有前進時也須產生新版本。
    monkeypatch.setattr(items_service, '_utcnow', lambda: as_utc(item['updated_at']))
    response = await client.patch(f"/api/items/{item['id']}", headers=auth_headers, json=body)
    assert response.status_code == 200
    updated = response.json()
    assert as_utc(updated['updated_at']) > as_utc(item['updated_at'])
    if 'tag_names' in body:
        assert [tag['name'] for tag in updated['tags']] == body['tag_names']
    persisted = (await client.get(f"/api/items/{item['id']}", headers=auth_headers)).json()
    assert as_utc(persisted['updated_at']) == as_utc(updated['updated_at'])


async def test_second_update_requires_new_timestamp(client, auth_headers, item):
    url = f"/api/items/{item['id']}"
    old_headers = {**auth_headers, 'If-Match': item['updated_at']}
    first = await client.patch(url, headers=old_headers, json={'tag_names': ['first']})
    assert first.status_code == 200
    second = await client.patch(url, headers=old_headers, json={'name': 'second'})
    assert second.status_code == 412
    assert as_utc(second.json()['detail']['current']['updated_at']) == as_utc(first.json()['updated_at'])
    retry = await client.patch(url, headers={
        **auth_headers, 'If-Match': first.json()['updated_at'],
    }, json={'name': 'second'})
    assert retry.status_code == 200
    assert retry.json()['name'] == 'second'
    assert as_utc(retry.json()['updated_at']) > as_utc(first.json()['updated_at'])


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
@pytest.mark.parametrize('timestamp', ['invalid', '2000-01-01T00:00:00Z'])
async def test_viewer_still_forbidden(client, viewer_auth, method, timestamp):
    response = await write(client, method, str(uuid4()), {**viewer_auth, 'If-Match': timestamp})
    assert response.status_code == 403


@pytest.mark.parametrize('method', ['PATCH', 'DELETE'])
@pytest.mark.parametrize('deleted', [False, True])
@pytest.mark.parametrize('timestamp', ['invalid', '2000-01-01T00:00:00Z'])
async def test_missing_or_deleted_precedes_header_check(
    client, auth_headers, item, method, deleted, timestamp,
):
    item_id = str(uuid4())
    if deleted:
        item_id = item['id']
        response = await client.delete(f'/api/items/{item_id}', headers={
            **auth_headers, 'If-Match': item['updated_at'],
        })
        assert response.status_code == 204
    response = await write(client, method, item_id, {**auth_headers, 'If-Match': timestamp})
    assert response.status_code == 404


@pytest.mark.parametrize('aware', [False, True])
async def test_database_timestamp_normalized_to_utc(aware):
    value = datetime(2026, 11, 14, 12, 0, 0, 123456)
    if aware:
        value = value.replace(tzinfo=timezone(timedelta(hours=8)))
    normalized = items_service._as_utc(value)
    assert normalized == datetime(2026, 11, 14, 4 if aware else 12, 0, 0, 123456, tzinfo=UTC)
