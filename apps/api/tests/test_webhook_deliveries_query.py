"""Phase 28 T1.1/T1.2 — deliveries 篩選／分頁參數與統計端點。

Seeds `WebhookDelivery` rows directly through `db_session` so `status_code`,
`next_retry_at`, `event` and `created_at` are fully controlled; then asserts
the public API contract (filters, offset pagination, stats aggregation).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.webhook import WebhookDelivery


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "whq@t.io", "username": "whq_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "whq_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _other_auth(client) -> dict:
    await client.post(
        "/api/auth/register",
        json={"email": "other@t.io", "username": "other_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "other_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_webhook(client, auth) -> str:
    r = await client.post(
        "/api/webhooks",
        headers=auth,
        json={"name": "t", "url": "http://example.com/hook", "events": ["item.created"]},
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _seed(db_session, webhook_id: str, specs: list[dict]) -> datetime:
    """Insert delivery rows. Each spec: excerpt / status_code / minutes_ago /
    optional event / attempt / next_retry. Returns the shared `now` anchor."""
    now = datetime.now(timezone.utc)
    for spec in specs:
        db_session.add(
            WebhookDelivery(
                webhook_id=webhook_id,
                event=spec.get("event", "item.created"),
                payload={"excerpt": spec["excerpt"]},
                status_code=spec["status_code"],
                response_excerpt=spec["excerpt"],
                attempt=spec.get("attempt", 1),
                next_retry_at=(
                    now + timedelta(seconds=30) if spec.get("next_retry") else None
                ),
                created_at=now - timedelta(minutes=spec["minutes_ago"]),
            )
        )
    await db_session.commit()
    return now


async def _list_excerpts(client, auth, webhook_id, **params) -> list[str]:
    r = await client.get(
        f"/api/webhooks/{webhook_id}/deliveries", headers=auth, params=params
    )
    assert r.status_code == 200, r.text
    return [row["response_excerpt"] for row in r.json()]


# Mixed fixture set: 1 success, 1 hard failure (no retry), 1 scheduled retry,
# 1 network failure with scheduled retry. Newest first order is
# network-retry, failed-retry, failed-500, success-old.
BASE = [
    {"excerpt": "success-old", "status_code": 200, "minutes_ago": 30},
    {"excerpt": "failed-500", "status_code": 500, "minutes_ago": 25},
    {"excerpt": "failed-retry", "status_code": 503, "minutes_ago": 20, "next_retry": True},
    {"excerpt": "network-retry", "status_code": None, "minutes_ago": 10, "next_retry": True},
]

STATS = [
    {"excerpt": "s-old", "status_code": 200, "minutes_ago": 30},
    {"excerpt": "f-500", "status_code": 500, "minutes_ago": 25},
    {"excerpt": "s-new", "status_code": 204, "minutes_ago": 10},
    {"excerpt": "n-retry", "status_code": None, "minutes_ago": 5, "next_retry": True},
]


# ---- T1.1: filters -------------------------------------------------------


async def test_filter_status_success(client, auth, db_session):
    wid = await _create_webhook(client, auth)
    await _seed(db_session, wid, BASE)

    assert await _list_excerpts(client, auth, wid, status="success") == ["success-old"]


async def test_filter_status_failed_includes_network_errors(client, auth, db_session):
    wid = await _create_webhook(client, auth)
    await _seed(db_session, wid, BASE)

    assert await _list_excerpts(client, auth, wid, status="failed") == [
        "network-retry",
        "failed-retry",
        "failed-500",
    ]


async def test_filter_status_pending(client, auth, db_session):
    wid = await _create_webhook(client, auth)
    await _seed(db_session, wid, BASE)

    assert await _list_excerpts(client, auth, wid, status="pending") == [
        "network-retry",
        "failed-retry",
    ]


async def test_filter_event(client, auth, db_session):
    wid = await _create_webhook(client, auth)
    await _seed(
        db_session,
        wid,
        [
            {"excerpt": "created-1", "status_code": 200, "minutes_ago": 30},
            {"excerpt": "updated-1", "status_code": 200, "minutes_ago": 20, "event": "item.updated"},
            {"excerpt": "created-2", "status_code": 200, "minutes_ago": 10},
        ],
    )

    assert await _list_excerpts(client, auth, wid, event="item.updated") == ["updated-1"]


# ---- T1.1: offset pagination --------------------------------------------


async def test_pagination_offset_newest_first(client, auth, db_session):
    wid = await _create_webhook(client, auth)
    await _seed(db_session, wid, BASE)

    assert await _list_excerpts(client, auth, wid, limit=2, offset=0) == [
        "network-retry",
        "failed-retry",
    ]
    assert await _list_excerpts(client, auth, wid, limit=2, offset=2) == [
        "failed-500",
        "success-old",
    ]
    assert await _list_excerpts(client, auth, wid, limit=2, offset=4) == []


async def test_combined_status_and_offset(client, auth, db_session):
    wid = await _create_webhook(client, auth)
    await _seed(
        db_session,
        wid,
        [
            {"excerpt": "s-old", "status_code": 200, "minutes_ago": 30},
            {"excerpt": "f-mid", "status_code": 500, "minutes_ago": 20},
            {"excerpt": "s-new", "status_code": 200, "minutes_ago": 10},
        ],
    )

    # offset applies after the status filter → second-newest success only.
    assert await _list_excerpts(client, auth, wid, status="success", offset=1, limit=1) == [
        "s-old"
    ]


async def test_invalid_status_rejected(client, auth, db_session):
    wid = await _create_webhook(client, auth)

    r = await client.get(
        f"/api/webhooks/{wid}/deliveries", headers=auth, params={"status": "weird"}
    )
    assert r.status_code == 422


async def test_deliveries_cross_owner_404(client, auth, db_session):
    other = await _other_auth(client)
    wid = await _create_webhook(client, other)

    r = await client.get(f"/api/webhooks/{wid}/deliveries", headers=auth)
    assert r.status_code == 404


# ---- T1.2: stats endpoint ------------------------------------------------


def _naive_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


async def test_stats_counts_and_last_success(client, auth, db_session):
    wid = await _create_webhook(client, auth)
    now = await _seed(db_session, wid, STATS)

    r = await client.get(f"/api/webhooks/{wid}/deliveries/stats", headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 4
    assert body["succeeded"] == 2
    assert body["failed"] == 2
    assert body["pending"] == 1

    got = _naive_utc(body["last_success_at"])
    expected = (now - timedelta(minutes=10)).replace(tzinfo=None)
    assert abs((got - expected).total_seconds()) <= 2
    # Definitely the newer success, not the older one 20 minutes earlier.
    stale = (now - timedelta(minutes=30)).replace(tzinfo=None)
    assert abs((got - stale).total_seconds()) > 60


async def test_stats_empty(client, auth, db_session):
    wid = await _create_webhook(client, auth)

    body = (
        await client.get(f"/api/webhooks/{wid}/deliveries/stats", headers=auth)
    ).json()
    assert body == {
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "pending": 0,
        "last_success_at": None,
    }


async def test_stats_cross_owner_404(client, auth, db_session):
    other = await _other_auth(client)
    wid = await _create_webhook(client, other)

    r = await client.get(f"/api/webhooks/{wid}/deliveries/stats", headers=auth)
    assert r.status_code == 404
