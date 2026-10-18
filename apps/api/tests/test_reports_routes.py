from __future__ import annotations

import calendar
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.models.report import Report

GENERATED_AT = datetime(2026, 10, 1, 0, 5, tzinfo=UTC)


async def _register(client, username: str) -> tuple[dict[str, str], UUID]:
    await client.post(
        "/api/auth/register",
        json={
            "email": f"{username}@t.io",
            "username": username,
            "password": "secret1234",
        },
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": username, "password": "secret1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = await client.get("/api/users/me", headers=headers)
    return headers, UUID(me.json()["id"])


def _payload(period: str, *, item_count: int = 42) -> dict:
    year, month = (int(part) for part in period.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    return {
        "version": 1,
        "period": period,
        "timezone": "Asia/Taipei",
        "period_start": date(year, month, 1).isoformat(),
        "period_end": date(year, month, last_day).isoformat(),
        "generated_at": GENERATED_AT.isoformat(),
        "currency": "TWD",
        "totals": {"item_count": item_count, "quantity": 7},
        "activity": {
            "items_created": 2,
            "items_deleted": 0,
            "quantity_in": 5,
            "quantity_out": 1,
            "loans_out": 1,
            "loans_returned": 0,
            "loans_overdue": 0,
        },
        "expiry": {"expiring_soon": 1, "expired": 0},
        "valuation": {
            "start": "10.00",
            "end": "12.00",
            "delta": "2.00",
            "unpriced_items": 0,
        },
        "top_categories": [{"label": "食品", "count": 3}],
        "top_locations": [{"label": "儲藏室", "count": 2}],
        "has_activity": True,
    }


def _report(user_id: UUID, period: str, **payload_kwargs) -> Report:
    return Report(
        user_id=user_id,
        period=period,
        payload=_payload(period, **payload_kwargs),
        generated_at=GENERATED_AT,
    )


async def test_reports_require_authentication(client):
    assert (await client.get("/api/reports")).status_code == 401
    assert (await client.get(f"/api/reports/{uuid4()}")).status_code == 401


async def test_list_returns_only_own_reports_sorted(client, db_session):
    alice_headers, alice_id = await _register(client, "rep_alice")
    _, bob_id = await _register(client, "rep_bob")

    august = _report(alice_id, "2026-08")
    september = _report(alice_id, "2026-09", item_count=99)
    db_session.add_all([august, september, _report(bob_id, "2026-09")])
    await db_session.commit()

    response = await client.get("/api/reports", headers=alice_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert [item["period"] for item in body["items"]] == ["2026-09", "2026-08"]
    assert body["items"][0]["payload"]["totals"]["item_count"] == 99


async def test_list_pagination_keeps_total(client, db_session):
    headers, user_id = await _register(client, "rep_page")
    db_session.add_all(
        [
            _report(user_id, "2026-07"),
            _report(user_id, "2026-08"),
            _report(user_id, "2026-09"),
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/api/reports?limit=1&offset=1", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["period"] for item in body["items"]] == ["2026-08"]


async def test_detail_returns_payload(client, db_session):
    headers, user_id = await _register(client, "rep_detail")
    report = _report(user_id, "2026-09", item_count=7)
    db_session.add(report)
    await db_session.commit()

    response = await client.get(
        f"/api/reports/{report.id}", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(report.id)
    assert body["period"] == "2026-09"
    assert body["payload"]["totals"]["item_count"] == 7
    assert body["payload"]["valuation"]["delta"] == "2.00"
    assert body["payload"]["top_categories"] == [{"label": "食品", "count": 3}]


async def test_detail_cannot_read_other_users_report(client, db_session):
    alice_headers, _ = await _register(client, "rep_owner")
    _, bob_id = await _register(client, "rep_other")
    bob_report = _report(bob_id, "2026-09")
    db_session.add(bob_report)
    await db_session.commit()

    response = await client.get(
        f"/api/reports/{bob_report.id}", headers=alice_headers
    )

    assert response.status_code == 404


async def test_detail_missing_report_404(client):
    headers, _ = await _register(client, "rep_missing")

    response = await client.get(f"/api/reports/{uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_list_limit_validation(client):
    headers, _ = await _register(client, "rep_limit")

    assert (
        await client.get("/api/reports?limit=0", headers=headers)
    ).status_code == 422
    assert (
        await client.get("/api/reports?limit=101", headers=headers)
    ).status_code == 422
