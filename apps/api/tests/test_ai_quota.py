from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.auth.password import hash_password
from app.clock import today_taipei
from app.models.ai_usage import AiUsage
from app.models.user import User
from app.services import ai_quota


async def _user(session, username: str = "quota_user") -> User:
    user = User(
        email=f"{username}@test.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


def _set_quota(monkeypatch, value: int) -> None:
    monkeypatch.setenv("AI_DAILY_QUOTA", str(value))
    from app.config import get_settings

    get_settings.cache_clear()


async def test_consume_accumulates_within_day(db_session, monkeypatch):
    _set_quota(monkeypatch, 2)
    user = await _user(db_session)
    day = date(2026, 10, 19)

    assert await ai_quota.consume(db_session, user.id, today=day) is True
    assert await ai_quota.consume(db_session, user.id, today=day) is True
    assert await ai_quota.consume(db_session, user.id, today=day) is False
    assert await ai_quota.consume(db_session, user.id, today=day) is False

    row = (
        await db_session.execute(select(AiUsage).where(AiUsage.user_id == user.id))
    ).scalar_one()
    assert row.day == day
    assert row.calls == 4


async def test_consume_per_user_isolation(db_session, monkeypatch):
    _set_quota(monkeypatch, 1)
    first = await _user(db_session, "quota_a")
    second = await _user(db_session, "quota_b")
    day = date(2026, 10, 19)

    assert await ai_quota.consume(db_session, first.id, today=day) is True
    assert await ai_quota.consume(db_session, first.id, today=day) is False
    assert await ai_quota.consume(db_session, second.id, today=day) is True


async def test_consume_resets_on_new_day(db_session, monkeypatch):
    _set_quota(monkeypatch, 1)
    user = await _user(db_session)
    first_day = date(2026, 10, 19)
    second_day = first_day + timedelta(days=1)

    assert await ai_quota.consume(db_session, user.id, today=first_day) is True
    assert await ai_quota.consume(db_session, user.id, today=first_day) is False
    assert await ai_quota.consume(db_session, user.id, today=second_day) is True

    days = (
        (
            await db_session.execute(
                select(AiUsage.day).where(AiUsage.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert sorted(days) == [first_day, second_day]


async def test_consume_unlimited_when_quota_non_positive(db_session, monkeypatch):
    _set_quota(monkeypatch, 0)
    user = await _user(db_session)
    day = date(2026, 10, 19)

    for _ in range(10):
        assert await ai_quota.consume(db_session, user.id, today=day) is True

    rows = (await db_session.execute(select(AiUsage))).scalars().all()
    assert rows == []


async def test_consume_uses_taipei_today(db_session, monkeypatch):
    _set_quota(monkeypatch, 5)
    user = await _user(db_session)

    assert await ai_quota.consume(db_session, user.id) is True

    row = (
        await db_session.execute(select(AiUsage).where(AiUsage.user_id == user.id))
    ).scalar_one()
    assert row.day == today_taipei()


async def test_consume_uses_injected_clock(db_session, monkeypatch):
    _set_quota(monkeypatch, 1)
    user = await _user(db_session)
    target = date(2026, 1, 2)
    monkeypatch.setattr(ai_quota, "today_taipei", lambda: target)

    assert await ai_quota.consume(db_session, user.id) is True
    assert await ai_quota.consume(db_session, user.id) is False

    row = (
        await db_session.execute(select(AiUsage).where(AiUsage.user_id == user.id))
    ).scalar_one()
    assert row.day == target
