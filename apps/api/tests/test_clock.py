from __future__ import annotations

from datetime import UTC, date, datetime

from app.clock import EXPIRING_SOON_DAYS, TAIPEI, days_left, expiry_status, today_taipei


def test_today_taipei_before_midnight():
    # 2026-10-15T15:59:59Z = 台北 2026-10-15 23:59:59
    assert today_taipei(datetime(2026, 10, 15, 15, 59, 59, tzinfo=UTC)) == date(
        2026, 10, 15
    )


def test_today_taipei_after_midnight():
    # 2026-10-15T16:00:00Z = 台北 2026-10-16 00:00:00
    assert today_taipei(datetime(2026, 10, 15, 16, 0, 0, tzinfo=UTC)) == date(
        2026, 10, 16
    )


def test_today_taipei_uses_system_now_when_not_injected():
    assert today_taipei() == datetime.now(TAIPEI).date()


def test_days_left_boundaries():
    today = date(2026, 10, 15)
    assert days_left(date(2026, 10, 15), today=today) == 0
    assert days_left(date(2026, 10, 14), today=today) == -1
    assert days_left(date(2026, 10, 22), today=today) == 7
    assert days_left(date(2026, 10, 23), today=today) == 8


def test_expiry_status_thresholds():
    today = date(2026, 10, 15)
    assert expiry_status(None, today=today) == "ok"
    assert expiry_status(date(2026, 10, 14), today=today) == "expired"
    assert expiry_status(date(2026, 10, 15), today=today) == "expiring"
    assert expiry_status(date(2026, 10, 22), today=today) == "expiring"
    assert expiry_status(date(2026, 10, 23), today=today) == "ok"


def test_expiring_soon_constant():
    assert EXPIRING_SOON_DAYS == 7
