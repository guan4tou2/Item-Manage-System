from datetime import UTC, datetime, timedelta

import pytest

from app.models.login_attempt import LoginAttempt
from app.services import login_throttle_service as throttle


def _ago(**kwargs) -> datetime:
    return datetime.now(UTC) - timedelta(**kwargs)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def _insert(
    session,
    *,
    kind: str,
    value: str,
    created_at: datetime,
) -> None:
    session.add(
        LoginAttempt(
            kind=kind,
            key_hash=throttle.key_hash(kind, value),
            created_at=created_at,
        )
    )
    await session.commit()


def test_key_hash_is_stable_and_does_not_contain_raw_value() -> None:
    first = throttle.key_hash("account", "alice@example.com")
    second = throttle.key_hash("account", "alice@example.com")

    assert first == second
    assert len(first) == 64
    assert "alice" not in first
    assert first != throttle.key_hash("ip", "alice@example.com")


async def test_account_locks_after_five_failures(db_session) -> None:
    for _ in range(5):
        status = await throttle.check(
            db_session, username="alice", ip="203.0.113.10"
        )
        assert status.blocked is False
        await throttle.record_failure(
            db_session, username="alice", ip="203.0.113.10"
        )

    status = await throttle.check(
        db_session, username="alice", ip="203.0.113.10"
    )

    assert status.blocked is True
    assert 0 < status.retry_after_seconds <= 15 * 60


async def test_unknown_username_uses_same_account_lockout(db_session) -> None:
    for _ in range(5):
        await throttle.record_failure(
            db_session, username="nobody-here", ip="203.0.113.11"
        )

    status = await throttle.check(
        db_session, username="nobody-here", ip="203.0.113.11"
    )

    assert status.blocked is True


async def test_success_resets_only_account_counter(db_session) -> None:
    for _ in range(5):
        await throttle.record_failure(
            db_session, username="alice", ip="203.0.113.12"
        )

    assert (
        await throttle.check(db_session, username="alice", ip="203.0.113.12")
    ).blocked is True

    await throttle.reset_account(db_session, username="alice")

    assert (
        await throttle.check(db_session, username="alice", ip="203.0.113.12")
    ).blocked is False

    # IP 的 5 次仍在；再 5 次不同帳號會觸發 10 次/1 分鐘的 IP 門檻。
    for index in range(5):
        await throttle.record_failure(
            db_session, username=f"other-{index}", ip="203.0.113.12"
        )

    status = await throttle.check(
        db_session, username="fresh-user", ip="203.0.113.12"
    )
    assert status.blocked is True


async def test_failures_outside_window_do_not_block(db_session) -> None:
    for _ in range(5):
        await _insert(
            db_session,
            kind="account",
            value="alice",
            created_at=_ago(minutes=16),
        )
        await _insert(
            db_session,
            kind="ip",
            value="203.0.113.13",
            created_at=_ago(minutes=16),
        )

    status = await throttle.check(
        db_session, username="alice", ip="203.0.113.13"
    )

    assert status.blocked is False


async def test_second_account_tier_uses_longer_lock(db_session) -> None:
    for _ in range(10):
        await _insert(
            db_session,
            kind="account",
            value="alice",
            created_at=_ago(minutes=5),
        )

    status = await throttle.check(
        db_session, username="alice", ip="203.0.113.14"
    )

    assert status.blocked is True
    # 第一級只會到 15 分鐘；第二級應超過它。
    assert status.retry_after_seconds > 15 * 60


async def test_second_account_tier_blocks_slow_spray(db_session) -> None:
    # 10 次分散在 54 分鐘內：最近 15 分鐘只有 3 次（不觸發第一級），
    # 但 1 小時內已達 10 次，第二級必須從最新一次起算 30 分鐘。
    for minutes_ago in range(54, -1, -6):
        await _insert(
            db_session,
            kind="account",
            value="alice",
            created_at=_ago(minutes=minutes_ago),
        )

    status = await throttle.check(
        db_session, username="alice", ip="203.0.113.20"
    )

    assert status.blocked is True
    assert 15 * 60 < status.retry_after_seconds <= 30 * 60


async def test_third_account_tier_caps_at_one_hour(db_session) -> None:
    for _ in range(15):
        await _insert(
            db_session,
            kind="account",
            value="alice",
            created_at=_ago(minutes=10),
        )

    status = await throttle.check(
        db_session, username="alice", ip="203.0.113.15"
    )

    assert status.blocked is True
    assert 30 * 60 < status.retry_after_seconds <= 60 * 60


async def test_ip_first_tier_locks_after_ten_failures_in_a_minute(
    db_session,
) -> None:
    for index in range(10):
        await throttle.record_failure(
            db_session,
            username=f"spray-{index}",
            ip="203.0.113.16",
        )

    status = await throttle.check(
        db_session, username="fresh-user", ip="203.0.113.16"
    )

    assert status.blocked is True
    assert 0 < status.retry_after_seconds <= 60


async def test_ip_second_tier_locks_after_thirty_failures(db_session) -> None:
    for index in range(30):
        await throttle.record_failure(
            db_session,
            username=f"spray-{index}",
            ip="203.0.113.17",
        )

    status = await throttle.check(
        db_session, username="fresh-user", ip="203.0.113.17"
    )

    assert status.blocked is True
    assert 60 < status.retry_after_seconds <= 15 * 60


async def test_record_failure_cleans_rows_older_than_retention(
    db_session,
) -> None:
    await _insert(
        db_session,
        kind="account",
        value="old-user",
        created_at=_ago(hours=25),
    )
    await _insert(
        db_session,
        kind="ip",
        value="198.51.100.99",
        created_at=_ago(hours=25),
    )

    await throttle.record_failure(
        db_session, username="alice", ip="203.0.113.18"
    )

    rows = (await db_session.execute(LoginAttempt.__table__.select())).all()
    assert len(rows) == 2  # 這次的 account + ip
    assert all(_utc(row.created_at) >= _ago(hours=24) for row in rows)


async def test_check_fails_open_when_storage_query_fails(
    db_session, monkeypatch
) -> None:
    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(throttle, "_load_timestamps", boom)

    status = await throttle.check(
        db_session, username="alice", ip="203.0.113.19"
    )

    assert status.blocked is False


async def test_record_failure_is_fail_soft(db_session, monkeypatch) -> None:
    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(throttle, "_persist_failure", boom)

    # 不應拋出；呼叫端仍可回原本的 401。
    await throttle.record_failure(
        db_session, username="alice", ip="203.0.113.20"
    )

    assert (
        await throttle.check(db_session, username="alice", ip="203.0.113.20")
    ).blocked is False


@pytest.mark.parametrize("retry_after", [0, 1, 59, 60, 900])
def test_throttle_status_retry_after_is_non_negative(retry_after: int) -> None:
    status = throttle.ThrottleStatus(
        blocked=retry_after > 0, retry_after_seconds=retry_after
    )
    assert status.retry_after_seconds >= 0
