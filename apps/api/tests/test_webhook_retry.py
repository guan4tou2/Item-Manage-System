from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import webhooks_service as svc


# ---- pure policy helpers -----------------------------------------------


def test_is_success_accepts_2xx():
    assert svc.is_success(200)
    assert svc.is_success(204)
    assert svc.is_success(299)


def test_is_success_rejects_non_2xx():
    assert not svc.is_success(None)
    assert not svc.is_success(199)
    assert not svc.is_success(300)
    assert not svc.is_success(404)
    assert not svc.is_success(500)


def test_backoff_after_returns_schedule():
    """30s → 2min → 8min → 30min, then None (exhausted)."""
    assert svc.backoff_after(1) == timedelta(seconds=30)
    assert svc.backoff_after(2) == timedelta(seconds=120)
    assert svc.backoff_after(3) == timedelta(seconds=480)
    assert svc.backoff_after(4) == timedelta(seconds=1800)
    # attempt 5 is the last — no further retry
    assert svc.backoff_after(5) is None
    assert svc.backoff_after(6) is None


def test_backoff_after_rejects_zero():
    # Attempt numbers are 1-indexed. 0 is nonsense and shouldn't crash.
    assert svc.backoff_after(0) is None


# ---- fixtures for the live-webhook tests -------------------------------


@pytest.fixture
async def auth(client):
    await client.post(
        "/api/auth/register",
        json={"email": "whr@t.io", "username": "whr_user", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "whr_user", "password": "secret1234"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _mock_httpx(monkeypatch, *, status: int | None, text: str = ""):
    """Patch httpx.AsyncClient to always return (status, text) or raise if
    status is None."""
    import httpx

    class MockResponse:
        def __init__(self):
            self.status_code = status
            self.text = text

    if status is None:
        mock_post = AsyncMock(side_effect=Exception("boom"))
    else:
        mock_post = AsyncMock(return_value=MockResponse())

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = mock_post
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)
    return mock_post


# ---- dispatch schedules retry on failure -------------------------------


async def test_failed_dispatch_schedules_retry(client, auth, monkeypatch):
    _mock_httpx(monkeypatch, status=503, text="nope")
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})

    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    assert len(deliveries) == 1
    row = deliveries[0]
    assert row["status_code"] == 503
    assert row["attempt"] == 1
    assert row["next_retry_at"] is not None


async def test_successful_dispatch_does_not_schedule_retry(client, auth, monkeypatch):
    _mock_httpx(monkeypatch, status=200, text="ok")
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})
    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    assert len(deliveries) == 1
    assert deliveries[0]["next_retry_at"] is None


async def test_network_failure_still_schedules_retry(client, auth, monkeypatch):
    _mock_httpx(monkeypatch, status=None)
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})
    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    assert len(deliveries) == 1
    assert deliveries[0]["status_code"] is None
    assert deliveries[0]["next_retry_at"] is not None


# ---- process-retries endpoint ------------------------------------------


async def test_process_retries_empty_when_nothing_due(client, auth, monkeypatch):
    # Nothing has fired yet; endpoint still works.
    r = await client.post("/api/webhooks/process-retries", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body == {"processed": 0, "succeeded": 0, "remaining": 0}


async def test_process_retries_reattempts_due_delivery(client, auth, db_session, monkeypatch):
    # Initial dispatch fails (503).
    mock = _mock_httpx(monkeypatch, status=503, text="nope")
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})

    # Manually set the scheduled retry into the past so it's "due".
    from sqlalchemy import select
    from app.models.webhook import WebhookDelivery

    row = (await db_session.execute(select(WebhookDelivery))).scalar_one()
    row.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()

    # Second attempt also fails.
    r = await client.post("/api/webhooks/process-retries", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["processed"] == 1
    assert body["succeeded"] == 0
    assert body["remaining"] == 1  # new attempt has its own next_retry_at

    # The deliveries list now contains attempt 1 (done) + attempt 2 (scheduled).
    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    attempts = sorted(d["attempt"] for d in deliveries)
    assert attempts == [1, 2]
    first = next(d for d in deliveries if d["attempt"] == 1)
    second = next(d for d in deliveries if d["attempt"] == 2)
    assert first["next_retry_at"] is None
    assert second["next_retry_at"] is not None


async def test_process_retries_stops_retrying_on_success(client, auth, db_session, monkeypatch):
    # First call fails, second call succeeds.
    call_count = {"n": 0}

    class MockResp:
        def __init__(self, status):
            self.status_code = status
            self.text = "ok" if status == 200 else "fail"

    async def fake_post(*args, **kwargs):
        call_count["n"] += 1
        return MockResp(503 if call_count["n"] == 1 else 200)

    import httpx

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = fake_post
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: mock_client)

    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})

    from sqlalchemy import select
    from app.models.webhook import WebhookDelivery

    row = (await db_session.execute(select(WebhookDelivery))).scalar_one()
    row.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()

    r = await client.post("/api/webhooks/process-retries", headers=auth)
    body = r.json()
    assert body["processed"] == 1
    assert body["succeeded"] == 1
    # Success → no more scheduled retries.
    assert body["remaining"] == 0

    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    second = next(d for d in deliveries if d["attempt"] == 2)
    assert second["status_code"] == 200
    assert second["next_retry_at"] is None


async def test_process_retries_gives_up_at_max_attempts(client, auth, db_session, monkeypatch):
    # All attempts fail.
    _mock_httpx(monkeypatch, status=503, text="fail")

    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})

    # Drive the retry loop until the service gives up.
    from sqlalchemy import select
    from app.models.webhook import WebhookDelivery

    for _ in range(10):  # plenty of iterations; should terminate within MAX_ATTEMPTS
        # Force all still-scheduled rows to be due.
        rows = list(
            (
                await db_session.execute(
                    select(WebhookDelivery).where(
                        WebhookDelivery.next_retry_at.is_not(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            break
        for r in rows:
            r.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db_session.commit()

        await client.post("/api/webhooks/process-retries", headers=auth)

    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    attempts = sorted(d["attempt"] for d in deliveries)
    assert attempts == [1, 2, 3, 4, svc.MAX_ATTEMPTS]
    # No delivery should still be scheduled.
    assert all(d["next_retry_at"] is None for d in deliveries)


async def test_process_retries_skips_deleted_webhook(client, auth, db_session, monkeypatch):
    _mock_httpx(monkeypatch, status=503)
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})

    # Make retry due, then delete webhook.
    from sqlalchemy import select
    from app.models.webhook import WebhookDelivery

    row = (await db_session.execute(select(WebhookDelivery))).scalar_one()
    row.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()

    await client.delete(f"/api/webhooks/{wh['id']}", headers=auth)
    r = await client.post("/api/webhooks/process-retries", headers=auth)
    # With CASCADE the delivery was deleted along with the webhook; the
    # process call has nothing to do. Either way the response should be
    # shape-correct and `remaining` must be 0.
    body = r.json()
    assert body["remaining"] == 0


# ---- manual retry endpoint --------------------------------------------


async def test_manual_retry_creates_new_attempt_row(client, auth, monkeypatch):
    _mock_httpx(monkeypatch, status=503)
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})

    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    did = deliveries[0]["id"]

    # Now swap mock to success and manually retry.
    _mock_httpx(monkeypatch, status=200, text="ok")
    r = await client.post(
        f"/api/webhooks/{wh['id']}/deliveries/{did}/retry", headers=auth
    )
    assert r.status_code == 200
    body = r.json()
    assert body["attempt"] == 2
    assert body["status_code"] == 200
    assert body["next_retry_at"] is None

    deliveries = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()
    assert len(deliveries) == 2


async def test_manual_retry_rejects_cross_owner(client, auth, monkeypatch):
    _mock_httpx(monkeypatch, status=503)
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    await client.post("/api/items", headers=auth, json={"name": "X"})
    did = (
        await client.get(f"/api/webhooks/{wh['id']}/deliveries", headers=auth)
    ).json()[0]["id"]

    await client.post(
        "/api/auth/register",
        json={"email": "other@t.io", "username": "other_wh", "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login",
        json={"username": "other_wh", "password": "secret1234"},
    )
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}

    resp = await client.post(
        f"/api/webhooks/{wh['id']}/deliveries/{did}/retry", headers=other
    )
    assert resp.status_code == 404


async def test_manual_retry_404_on_unknown_delivery(client, auth):
    wh = (
        await client.post(
            "/api/webhooks",
            headers=auth,
            json={"name": "t", "url": "http://example.com/hook"},
        )
    ).json()
    fake_delivery = "00000000-0000-0000-0000-000000000000"
    r = await client.post(
        f"/api/webhooks/{wh['id']}/deliveries/{fake_delivery}/retry", headers=auth
    )
    assert r.status_code == 404


async def test_process_retries_requires_auth(client):
    r = await client.post("/api/webhooks/process-retries")
    assert r.status_code == 401
