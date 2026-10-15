from __future__ import annotations

from datetime import timedelta

import pytest

from app.clock import today_taipei


def _days_from_today(days: int) -> str:
    return (today_taipei() + timedelta(days=days)).isoformat()


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "batches@t.io", "username": "batches_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "batches_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_item(client, headers, **overrides) -> str:
    body = {"name": "牛奶", "quantity": 5, **overrides}
    resp = await client.post("/api/items", headers=headers, json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_batch(client, headers, item_id: str, **body) -> dict:
    resp = await client.post(
        f"/api/items/{item_id}/batches", headers=headers, json=body
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestBatchesCrud:
    async def test_first_batch_absorbs_quantity(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)

        batch = await _create_batch(client, auth_headers, item_id)

        assert batch["quantity"] == 5
        assert batch["days_left"] is None
        assert batch["status"] == "ok"
        item = (await client.get(f"/api/items/{item_id}", headers=auth_headers)).json()
        assert item["track_batches"] is True
        assert item["quantity"] == 5

    async def test_create_with_expiry_derives_status(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)

        expiring = await _create_batch(
            client, auth_headers, item_id, quantity=2, expiry_date=_days_from_today(5)
        )
        assert expiring["days_left"] == 5
        assert expiring["status"] == "expiring"

        expired = await _create_batch(
            client, auth_headers, item_id, quantity=1, expiry_date=_days_from_today(-1)
        )
        assert expired["days_left"] == -1
        assert expired["status"] == "expired"

    async def test_second_batch_requires_quantity(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        await _create_batch(client, auth_headers, item_id)

        resp = await client.post(
            f"/api/items/{item_id}/batches", headers=auth_headers, json={}
        )
        assert resp.status_code == 422

    async def test_quantity_zero_is_422(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        resp = await client.post(
            f"/api/items/{item_id}/batches",
            headers=auth_headers,
            json={"quantity": 0},
        )
        assert resp.status_code == 422

    async def test_list_active_before_depleted(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        keep = await _create_batch(client, auth_headers, item_id, quantity=1)
        gone = await _create_batch(
            client, auth_headers, item_id, quantity=1, expiry_date=_days_from_today(2)
        )
        resp = await client.post(
            f"/api/items/{item_id}/batches/{gone['id']}/consume",
            headers=auth_headers,
            json={"quantity": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["is_depleted"] is True

        listed = (
            await client.get(f"/api/items/{item_id}/batches", headers=auth_headers)
        ).json()
        assert [b["id"] for b in listed] == [keep["id"], gone["id"]]
        assert listed[-1]["is_depleted"] is True

    async def test_patch_batch_updates_quantity_and_note(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        batch = await _create_batch(client, auth_headers, item_id)

        resp = await client.patch(
            f"/api/items/{item_id}/batches/{batch['id']}",
            headers=auth_headers,
            json={"quantity": 8, "note": "冰箱"},
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 8
        assert resp.json()["note"] == "冰箱"
        item = (await client.get(f"/api/items/{item_id}", headers=auth_headers)).json()
        assert item["quantity"] == 8

    async def test_delete_batch_and_repeat_404(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        batch = await _create_batch(client, auth_headers, item_id)

        resp = await client.delete(
            f"/api/items/{item_id}/batches/{batch['id']}", headers=auth_headers
        )
        assert resp.status_code == 204
        item = (await client.get(f"/api/items/{item_id}", headers=auth_headers)).json()
        assert item["quantity"] == 0

        resp = await client.delete(
            f"/api/items/{item_id}/batches/{batch['id']}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_disable_merges_and_returns_item(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        await _create_batch(client, auth_headers, item_id)

        resp = await client.post(
            f"/api/items/{item_id}/batches/disable", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["track_batches"] is False
        assert body["quantity"] == 5

        listed = (
            await client.get(f"/api/items/{item_id}/batches", headers=auth_headers)
        ).json()
        assert listed == []


class TestConsume:
    async def test_fefo_endpoint_consumes_earliest_first(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers, quantity=0)
        early = await _create_batch(
            client, auth_headers, item_id, quantity=2, expiry_date=_days_from_today(3)
        )
        late = await _create_batch(
            client, auth_headers, item_id, quantity=2, expiry_date=_days_from_today(10)
        )

        resp = await client.post(
            f"/api/items/{item_id}/consume", headers=auth_headers, json={"quantity": 3}
        )
        assert resp.status_code == 200
        assert resp.json()["consumed"] == [
            {"batch_id": early["id"], "quantity": 2},
            {"batch_id": late["id"], "quantity": 1},
        ]
        item = (await client.get(f"/api/items/{item_id}", headers=auth_headers)).json()
        assert item["quantity"] == 1

    async def test_fefo_insufficient_is_409(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        await _create_batch(client, auth_headers, item_id)

        resp = await client.post(
            f"/api/items/{item_id}/consume", headers=auth_headers, json={"quantity": 99}
        )
        assert resp.status_code == 409

    async def test_single_batch_consume_over_is_409(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        batch = await _create_batch(client, auth_headers, item_id)

        resp = await client.post(
            f"/api/items/{item_id}/batches/{batch['id']}/consume",
            headers=auth_headers,
            json={"quantity": 6},
        )
        assert resp.status_code == 409


class TestAuthAndOwnership:
    async def test_unauthenticated_401(self, client):
        resp = await client.get(
            "/api/items/00000000-0000-0000-0000-000000000000/batches"
        )
        assert resp.status_code == 401

    async def test_foreign_owner_404(self, client, auth_headers):
        item_id = await _create_item(client, auth_headers)
        await client.post("/api/auth/register", json={
            "email": "other@t.io", "username": "other_user", "password": "secret1234",
        })
        login = await client.post("/api/auth/login", json={
            "username": "other_user", "password": "secret1234",
        })
        other = {"Authorization": f"Bearer {login.json()['access_token']}"}

        assert (
            await client.get(f"/api/items/{item_id}/batches", headers=other)
        ).status_code == 404
        assert (
            await client.post(f"/api/items/{item_id}/batches", headers=other, json={})
        ).status_code == 404
        assert (
            await client.post(f"/api/items/{item_id}/consume", headers=other, json={"quantity": 1})
        ).status_code == 404
