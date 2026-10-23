from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.auth.password import hash_password
from app.models.item import Item
from app.models.notification import Notification
from app.models.report import Report
from app.models.user import User
from app.schemas.preferences import PreferencesUpdate
from app.services import (
    external_notifications,
    jobs_service,
    preferences_service,
    reports_service,
)

TODAY = date(2026, 10, 18)
WEEKLY_RUN_DAY = date(2026, 10, 19)
SEPTEMBER = "2026-09"


async def _user(session, username: str, *, email: str | None = None) -> User:
    user = User(
        email=email or f"{username}@test.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


async def _item(session, owner: User, **fields) -> Item:
    item = Item(owner_id=owner.id, name=fields.pop("name", "物品"), **fields)
    session.add(item)
    await session.flush()
    return item


async def _set_prefs(session, user: User, **fields) -> None:
    await preferences_service.update_preferences(
        session, user_id=user.id, update=PreferencesUpdate(**fields)
    )


async def _reports(session, user: User) -> list[Report]:
    stmt = select(Report).where(Report.user_id == user.id)
    return list((await session.execute(stmt)).scalars().all())


async def _notifications(session, user: User) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    return list((await session.execute(stmt)).scalars().all())


@pytest.fixture
def emails(monkeypatch):
    calls: list[dict] = []

    async def fake(to_email, subject, body, *, html=None):
        calls.append(
            {"to": to_email, "subject": subject, "body": body, "html": html}
        )
        return True

    monkeypatch.setattr(external_notifications, "deliver_email", fake)
    return calls


async def test_generate_monthly_creates_report_and_delivers(db_session, emails):
    user = await _user(db_session, "job_active")
    await _item(
        db_session,
        user,
        name="本月新增",
        quantity=2,
        cost=Decimal("2.00"),
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    await db_session.commit()

    result = await reports_service.generate_monthly(db_session, TODAY)

    assert result.processed == 1
    assert result.emitted == 1
    assert result.errors == []

    reports = await _reports(db_session, user)
    assert len(reports) == 1
    report = reports[0]
    assert report.period == SEPTEMBER
    assert report.payload["has_activity"] is True
    assert report.payload["totals"]["item_count"] == 1

    notifications = await _notifications(db_session, user)
    assert len(notifications) == 1
    assert notifications[0].type == "report_ready"
    assert notifications[0].link == f"/reports/{report.id}"

    assert len(emails) == 1
    assert "2026 年 9 月" in emails[0]["subject"]
    assert emails[0]["html"] is not None
    assert "月報" in emails[0]["html"]
    assert f"/reports/{report.id}" in emails[0]["body"]


async def test_generate_monthly_is_idempotent(db_session, emails):
    user = await _user(db_session, "job_twice")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    await db_session.commit()

    first = await reports_service.generate_monthly(db_session, TODAY)
    second = await reports_service.generate_monthly(db_session, TODAY)

    assert first.processed == 1
    assert second.processed == 0
    assert second.emitted == 0
    assert len(await _reports(db_session, user)) == 1
    assert len(await _notifications(db_session, user)) == 1
    assert len(emails) == 1


async def test_generate_monthly_quiet_month_creates_trace_without_delivery(
    db_session, emails
):
    user = await _user(db_session, "job_quiet")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    await db_session.commit()

    result = await reports_service.generate_monthly(db_session, TODAY)

    assert result.processed == 1
    assert result.emitted == 0
    reports = await _reports(db_session, user)
    assert len(reports) == 1
    assert reports[0].payload["has_activity"] is False
    assert await _notifications(db_session, user) == []
    assert emails == []


async def test_generate_monthly_respects_master_switch(db_session, emails):
    user = await _user(db_session, "job_off")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    await _set_prefs(db_session, user, report_monthly_enabled=False)
    await db_session.commit()

    result = await reports_service.generate_monthly(db_session, TODAY)

    assert result.processed == 0
    assert await _reports(db_session, user) == []
    assert emails == []


async def test_generate_monthly_skips_users_without_items(db_session, emails):
    user = await _user(db_session, "job_empty")
    await db_session.commit()

    result = await reports_service.generate_monthly(db_session, TODAY)

    assert result.processed == 0
    assert await _reports(db_session, user) == []


async def test_generate_monthly_email_pref_off_keeps_in_app(db_session, emails):
    user = await _user(db_session, "job_no_email")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    from app.models.notification_preference import NotificationPreference

    db_session.add(
        NotificationPreference(
            user_id=user.id, type="report_ready", channel="email", enabled=False
        )
    )
    await db_session.commit()

    result = await reports_service.generate_monthly(db_session, TODAY)

    assert result.processed == 1
    assert result.emitted == 1
    assert emails == []
    assert len(await _notifications(db_session, user)) == 1


async def test_generate_monthly_email_failure_is_fail_soft(
    db_session, monkeypatch
):
    user = await _user(db_session, "job_bad_smtp")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    await db_session.commit()

    async def failing_email(to_email, subject, body, *, html=None):
        return False

    monkeypatch.setattr(external_notifications, "deliver_email", failing_email)

    result = await reports_service.generate_monthly(db_session, TODAY)

    assert result.errors == []
    assert result.processed == 1
    assert result.emitted == 1  # 站內通知仍成立
    assert len(await _notifications(db_session, user)) == 1


async def test_generate_monthly_uses_user_language(db_session, emails):
    user = await _user(db_session, "job_en")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    await _set_prefs(db_session, user, language="en")
    await db_session.commit()

    await reports_service.generate_monthly(db_session, TODAY)

    notifications = await _notifications(db_session, user)
    assert "September 2026" in notifications[0].title
    assert "September 2026" in emails[0]["subject"]


async def test_generate_monthly_isolates_user_failures(db_session, monkeypatch):
    broken = await _user(db_session, "job_broken")
    healthy = await _user(db_session, "job_healthy")
    for user in (broken, healthy):
        await _item(
            db_session,
            user,
            quantity=1,
            created_at=datetime(2026, 9, 10, tzinfo=UTC),
        )
    await db_session.commit()

    original = reports_service.build_payload
    broken_id = broken.id

    async def flaky(session, **kwargs):
        if kwargs["user_id"] == broken_id:
            raise RuntimeError("boom")
        return await original(session, **kwargs)

    monkeypatch.setattr(reports_service, "build_payload", flaky)

    result = await reports_service.generate_monthly(db_session, TODAY)

    assert result.processed == 1
    assert len(result.errors) == 1
    assert str(broken_id) in result.errors[0]
    assert "boom" in result.errors[0]
    healthy_reports = (
        await db_session.execute(select(Report).where(Report.user_id == healthy.id))
    ).scalars().all()
    broken_reports = (
        await db_session.execute(select(Report).where(Report.user_id == broken_id))
    ).scalars().all()
    assert len(healthy_reports) == 1
    assert list(broken_reports) == []


async def test_report_monthly_job_is_registered_and_runs(db_session):
    spec = jobs_service.JOBS.get("report.monthly")
    assert spec is not None

    row = await jobs_service.run_job(db_session, "report.monthly")

    assert row.job_name == "report.monthly"
    assert row.status == "succeeded"
    assert isinstance(row.result["processed"], int)
    assert await db_session.scalar(select(func.count(Report.id))) == 0


async def test_generate_weekly_creates_report_and_delivers(db_session, emails):
    """Phase 42：週報為上一個完整 ISO 週，通知／Email 使用週報用語。"""
    user = await _user(db_session, "job_weekly")
    await _item(
        db_session,
        user,
        name="上週新增",
        quantity=2,
        cost=Decimal("2.00"),
        created_at=datetime(2026, 10, 14, tzinfo=UTC),
    )
    await _set_prefs(db_session, user, report_weekly_enabled=True)
    await db_session.commit()

    result = await reports_service.generate_weekly(db_session, WEEKLY_RUN_DAY)

    assert result.processed == 1
    assert result.emitted == 1
    assert result.errors == []

    reports = await _reports(db_session, user)
    assert len(reports) == 1
    report = reports[0]
    assert report.kind == "weekly"
    assert report.period == "2026-W42"
    assert report.payload["kind"] == "weekly"
    assert report.payload["period"] == "2026-W42"
    assert report.payload["period_start"] == "2026-10-12"
    assert report.payload["period_end"] == "2026-10-18"
    assert report.payload["has_activity"] is True

    notifications = await _notifications(db_session, user)
    assert len(notifications) == 1
    assert notifications[0].type == "report_ready"
    assert "週報已生成" in notifications[0].title
    assert "2026 年 10 月 12–18 日" in notifications[0].title
    assert notifications[0].link == f"/reports/{report.id}"

    assert len(emails) == 1
    assert "週報已生成" in emails[0]["subject"]
    assert "本週動態" in emails[0]["html"]
    assert f"/reports/{report.id}" in emails[0]["body"]


async def test_generate_weekly_defaults_off(db_session, emails):
    """Phase 42：週報預設關閉；未開啟不生成、不寄信。"""
    user = await _user(db_session, "job_weekly_off")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 10, 14, tzinfo=UTC),
    )
    await db_session.commit()

    result = await reports_service.generate_weekly(db_session, WEEKLY_RUN_DAY)

    assert result.processed == 0
    assert await _reports(db_session, user) == []
    assert emails == []


async def test_generate_weekly_is_idempotent(db_session, emails):
    user = await _user(db_session, "job_weekly_twice")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 10, 14, tzinfo=UTC),
    )
    await _set_prefs(db_session, user, report_weekly_enabled=True)
    await db_session.commit()

    first = await reports_service.generate_weekly(db_session, WEEKLY_RUN_DAY)
    second = await reports_service.generate_weekly(db_session, WEEKLY_RUN_DAY)

    assert first.processed == 1
    assert second.processed == 0
    assert second.emitted == 0
    assert len(await _reports(db_session, user)) == 1
    assert len(await _notifications(db_session, user)) == 1
    assert len(emails) == 1


async def test_generate_weekly_quiet_week_creates_trace_without_delivery(
    db_session, emails
):
    user = await _user(db_session, "job_weekly_quiet")
    await _item(
        db_session,
        user,
        quantity=1,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    await _set_prefs(db_session, user, report_weekly_enabled=True)
    await db_session.commit()

    result = await reports_service.generate_weekly(db_session, WEEKLY_RUN_DAY)

    assert result.processed == 1
    assert result.emitted == 0
    reports = await _reports(db_session, user)
    assert len(reports) == 1
    assert reports[0].payload["has_activity"] is False
    assert await _notifications(db_session, user) == []
    assert emails == []


async def test_generate_weekly_skips_users_without_items(db_session, emails):
    user = await _user(db_session, "job_weekly_empty")
    await _set_prefs(db_session, user, report_weekly_enabled=True)
    await db_session.commit()

    result = await reports_service.generate_weekly(db_session, WEEKLY_RUN_DAY)

    assert result.processed == 0
    assert await _reports(db_session, user) == []


async def test_report_weekly_job_is_registered_and_runs(db_session):
    spec = jobs_service.JOBS.get("report.weekly")
    assert spec is not None
    assert spec.stale_after_hours == 170

    row = await jobs_service.run_job(db_session, "report.weekly")

    assert row.job_name == "report.weekly"
    assert row.status == "succeeded"
    assert isinstance(row.result["processed"], int)
    assert await db_session.scalar(select(func.count(Report.id))) == 0
