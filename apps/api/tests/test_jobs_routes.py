from __future__ import annotations

from datetime import timedelta

import pytest

from app.clock import today_taipei
from app.models.item import Item
from app.models.item_batch import ItemBatch


async def _register_and_login(client, username):
    await client.post(
        "/api/auth/register",
        json={"email": f"{username}@t.io", "username": username, "password": "secret1234"},
    )
    r = await client.post(
        "/api/auth/login", json={"username": username, "password": "secret1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _make_admin(client, headers):
    r = await client.post("/api/auth/bootstrap-admin", headers=headers)
    assert r.status_code == 200
    return headers


@pytest.fixture
async def admin_auth(client):
    h = await _register_and_login(client, "jobs_admin")
    return await _make_admin(client, h)


@pytest.fixture
async def regular_auth(client):
    return await _register_and_login(client, "jobs_user")


async def _seed_batch(client, db_session, headers, *, expiry_in: int = 3) -> None:
    me = (await client.get("/api/users/me", headers=headers)).json()
    item = Item(owner_id=me["id"], name="牛奶")
    db_session.add(item)
    await db_session.flush()
    db_session.add(
        ItemBatch(
            item_id=item.id,
            quantity=1,
            expiry_date=today_taipei() + timedelta(days=expiry_in),
        )
    )
    await db_session.commit()


async def test_run_requires_authentication(client):
    r = await client.post("/api/jobs/expiry-scan/run")
    assert r.status_code == 401


async def test_run_forbidden_for_non_admin(client, regular_auth):
    r = await client.post("/api/jobs/expiry-scan/run", headers=regular_auth)
    assert r.status_code == 403


async def test_run_unknown_job_404(client, admin_auth):
    r = await client.post("/api/jobs/nope/run", headers=admin_auth)
    assert r.status_code == 404


async def test_run_success_records_and_status(client, admin_auth, db_session):
    await _seed_batch(client, db_session, admin_auth)

    r = await client.post("/api/jobs/expiry-scan/run", headers=admin_auth)

    assert r.status_code == 200
    assert r.json() == {
        "job": "expiry-scan",
        "status": "succeeded",
        "processed": 2,
        "emitted": 1,
    }

    s = await client.get("/api/jobs/expiry-scan/status", headers=admin_auth)
    assert s.status_code == 200
    body = s.json()
    assert body["job"] == "expiry-scan"
    assert body["stale"] is False
    assert body["thresholds"] == {
        "stale_after_hours": 26,
        "advance_days": [30, 7, 0],
        "expired_stop_days": 14,
    }
    assert body["last_run"]["status"] == "succeeded"
    assert body["last_run"]["result"]["processed"] == 2
    assert body["last_run"]["finished_at"] is not None

    # run 後：儀表板到期卡註記來源
    stats = (await client.get("/api/stats/expiry", headers=admin_auth)).json()
    assert stats["reminded_today"] is True


async def test_run_same_day_idempotent(client, admin_auth, db_session):
    await _seed_batch(client, db_session, admin_auth)

    await client.post("/api/jobs/expiry-scan/run", headers=admin_auth)
    r = await client.post("/api/jobs/expiry-scan/run", headers=admin_auth)

    assert r.json()["processed"] == 0
    assert r.json()["emitted"] == 0


async def test_status_never_run_for_regular_user(client, regular_auth):
    s = await client.get("/api/jobs/expiry-scan/status", headers=regular_auth)
    assert s.status_code == 200
    assert s.json()["last_run"] is None
    assert s.json()["stale"] is True


async def test_status_unknown_job_404(client, regular_auth):
    r = await client.get("/api/jobs/nope/status", headers=regular_auth)
    assert r.status_code == 404


async def test_status_requires_authentication(client):
    r = await client.get("/api/jobs/expiry-scan/status")
    assert r.status_code == 401


async def test_admin_pat_can_trigger(client, admin_auth, db_session):
    await _seed_batch(client, db_session, admin_auth)
    created = (
        await client.post(
            "/api/users/me/tokens", headers=admin_auth, json={"name": "cron"}
        )
    ).json()
    pat = {"Authorization": f"Bearer {created['token']}"}

    r = await client.post("/api/jobs/expiry-scan/run", headers=pat)

    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"


async def test_report_monthly_job_status_and_run(client, admin_auth):
    """Phase 31：月報 job 需註冊在 registry 且可經管理員觸發。"""
    s = await client.get("/api/jobs/report.monthly/status", headers=admin_auth)
    assert s.status_code == 200
    body = s.json()
    assert body["job"] == "report.monthly"
    assert body["last_run"] is None

    r = await client.post("/api/jobs/report.monthly/run", headers=admin_auth)

    assert r.status_code == 200
    assert r.json()["job"] == "report.monthly"
    assert r.json()["status"] == "succeeded"
    assert r.json()["processed"] == 0


async def test_report_job_thresholds_are_per_job(client, admin_auth):
    """Phase 42：月報／週報的 stale 門檻各自放寬（不再固定 26h）。"""
    monthly = await client.get(
        "/api/jobs/report.monthly/status", headers=admin_auth
    )
    assert monthly.status_code == 200
    assert monthly.json()["thresholds"]["stale_after_hours"] == 770
    assert monthly.json()["stale"] is True

    weekly = await client.get(
        "/api/jobs/report.weekly/status", headers=admin_auth
    )
    assert weekly.status_code == 200
    assert weekly.json()["job"] == "report.weekly"
    assert weekly.json()["thresholds"]["stale_after_hours"] == 170
    assert weekly.json()["last_run"] is None
    assert weekly.json()["stale"] is True

    # 跑完月報後，同一個 job 立即不再 stale（門檻為 770h）
    run = await client.post(
        "/api/jobs/report.monthly/run", headers=admin_auth
    )
    assert run.status_code == 200
    refreshed = await client.get(
        "/api/jobs/report.monthly/status", headers=admin_auth
    )
    assert refreshed.json()["stale"] is False
