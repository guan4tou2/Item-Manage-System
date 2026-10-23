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


def _payload(
    period: str,
    *,
    item_count: int = 42,
    kind: str = "monthly",
    start: date | None = None,
    end: date | None = None,
    include_kind: bool = True,
) -> dict:
    if kind == "weekly":
        assert start is not None and end is not None
        period_start, period_end = start, end
    else:
        year, month = (int(part) for part in period.split("-"))
        last_day = calendar.monthrange(year, month)[1]
        period_start = date(year, month, 1)
        period_end = date(year, month, last_day)
    payload = {
        "version": 1,
        "period": period,
        "timezone": "Asia/Taipei",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
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
    if include_kind:
        payload["kind"] = kind
    return payload


def _report(
    user_id: UUID,
    period: str,
    *,
    kind: str = "monthly",
    generated_at: datetime = GENERATED_AT,
    include_kind: bool = True,
    **payload_kwargs,
) -> Report:
    return Report(
        user_id=user_id,
        period=period,
        kind=kind,
        payload=_payload(
            period, kind=kind, include_kind=include_kind, **payload_kwargs
        ),
        generated_at=generated_at,
    )


def _weekly_report(
    user_id: UUID,
    *,
    period: str = "2026-W42",
    generated_at: datetime = GENERATED_AT,
    **payload_kwargs,
) -> Report:
    return _report(
        user_id,
        period,
        kind="weekly",
        generated_at=generated_at,
        start=date(2026, 10, 12),
        end=date(2026, 10, 18),
        **payload_kwargs,
    )


async def test_reports_require_authentication(client):
    assert (await client.get("/api/reports")).status_code == 401
    assert (await client.get(f"/api/reports/{uuid4()}")).status_code == 401


async def test_list_returns_only_own_reports_sorted(client, db_session):
    alice_headers, alice_id = await _register(client, "rep_alice")
    _, bob_id = await _register(client, "rep_bob")

    august = _report(
        alice_id,
        "2026-08",
        generated_at=datetime(2026, 9, 1, 0, 5, tzinfo=UTC),
    )
    september = _report(
        alice_id,
        "2026-09",
        item_count=99,
        generated_at=datetime(2026, 10, 1, 0, 5, tzinfo=UTC),
    )
    db_session.add_all(
        [
            august,
            september,
            _report(
                bob_id,
                "2026-09",
                generated_at=datetime(2026, 10, 2, 0, 5, tzinfo=UTC),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/reports", headers=alice_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert [item["period"] for item in body["items"]] == ["2026-09", "2026-08"]
    assert [item["kind"] for item in body["items"]] == ["monthly", "monthly"]
    assert body["items"][0]["payload"]["totals"]["item_count"] == 99


async def test_list_pagination_keeps_total(client, db_session):
    headers, user_id = await _register(client, "rep_page")
    db_session.add_all(
        [
            _report(
                user_id,
                "2026-07",
                generated_at=datetime(2026, 8, 1, 0, 5, tzinfo=UTC),
            ),
            _report(
                user_id,
                "2026-08",
                generated_at=datetime(2026, 9, 1, 0, 5, tzinfo=UTC),
            ),
            _report(
                user_id,
                "2026-09",
                generated_at=datetime(2026, 10, 1, 0, 5, tzinfo=UTC),
            ),
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


async def test_list_mixed_weekly_and_monthly_sorted_by_generated_at(
    client, db_session
):
    """Phase 42：週／月混排以 generated_at 新到舊，不靠 period 字典序。"""
    headers, user_id = await _register(client, "rep_mixed")
    september = _report(
        user_id,
        "2026-09",
        generated_at=datetime(2026, 10, 1, 0, 5, tzinfo=UTC),
    )
    weekly = _weekly_report(
        user_id,
        generated_at=datetime(2026, 10, 19, 0, 5, tzinfo=UTC),
    )
    db_session.add_all([september, weekly])
    await db_session.commit()

    response = await client.get("/api/reports", headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["kind"] for item in items] == ["weekly", "monthly"]
    assert [item["period"] for item in items] == ["2026-W42", "2026-09"]


async def test_detail_weekly_kind_and_payload(client, db_session):
    headers, user_id = await _register(client, "rep_weekly")
    report = _weekly_report(user_id)
    db_session.add(report)
    await db_session.commit()

    response = await client.get(
        f"/api/reports/{report.id}", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "weekly"
    assert body["period"] == "2026-W42"
    assert body["payload"]["kind"] == "weekly"
    assert body["payload"]["period_start"] == "2026-10-12"
    assert body["payload"]["period_end"] == "2026-10-18"


async def test_old_payload_without_kind_defaults_to_monthly(client, db_session):
    """Phase 42：Phase 31 的舊 payload 沒有 kind，仍應驗證為月報。"""
    headers, user_id = await _register(client, "rep_legacy")
    report = _report(user_id, "2026-09", include_kind=False)
    db_session.add(report)
    await db_session.commit()

    response = await client.get(
        f"/api/reports/{report.id}", headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "monthly"
    assert body["payload"]["kind"] == "monthly"


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
    assert body["kind"] == "monthly"
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
