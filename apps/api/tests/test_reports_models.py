from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.auth.password import hash_password
from app.models.report import Report
from app.models.user import User


async def _user(session, username: str = "reports_user") -> User:
    user = User(
        email=f"{username}@test.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


async def test_report_roundtrip_defaults(db_session):
    user = await _user(db_session)
    report = Report(
        user_id=user.id,
        period="2026-09",
        payload={"version": 1, "period": "2026-09"},
    )
    db_session.add(report)
    await db_session.commit()

    assert report.id is not None
    assert report.generated_at is not None
    assert report.payload["period"] == "2026-09"
    # Phase 42：既有列／未指定時預設為月報
    assert report.kind == "monthly"


async def test_report_weekly_period_and_kind_roundtrip(db_session):
    """Phase 42：period 放寬到 10，可存 ISO 週 key；kind 區分週／月。"""
    user = await _user(db_session)
    weekly = Report(
        user_id=user.id,
        period="2026-W42",
        kind="weekly",
        payload={"version": 1, "kind": "weekly", "period": "2026-W42"},
    )
    db_session.add(weekly)
    await db_session.commit()

    assert weekly.kind == "weekly"
    assert weekly.period == "2026-W42"
    assert Report.__table__.c.period.type.length == 10
    assert Report.__table__.c.kind.type.length == 8


async def test_report_unique_per_user_and_period(db_session):
    user = await _user(db_session)
    db_session.add(
        Report(user_id=user.id, period="2026-09", payload={"version": 1})
    )
    await db_session.commit()

    db_session.add(
        Report(user_id=user.id, period="2026-09", payload={"version": 1})
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_report_same_period_allowed_for_different_users(db_session):
    first = await _user(db_session, "reports_a")
    second = await _user(db_session, "reports_b")
    db_session.add_all(
        [
            Report(user_id=first.id, period="2026-09", payload={"version": 1}),
            Report(user_id=second.id, period="2026-09", payload={"version": 1}),
        ]
    )
    await db_session.commit()

    rows = (await db_session.execute(select(Report))).scalars().all()
    assert len(rows) == 2


async def test_report_cascade_delete_with_user(db_session):
    user = await _user(db_session)
    report = Report(user_id=user.id, period="2026-09", payload={"version": 1})
    db_session.add(report)
    await db_session.commit()
    report_id = report.id

    # SQLite 預設不啟用 FK；開啟後驗證 DB 層 CASCADE 定義
    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    await db_session.delete(user)
    await db_session.commit()

    remaining = (
        await db_session.execute(select(Report).where(Report.id == report_id))
    ).scalar_one_or_none()
    assert remaining is None
