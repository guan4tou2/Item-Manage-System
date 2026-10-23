"""登入失敗節流（Phase 43）。

以資料庫保存每次失敗（account／ip），用時間窗分級鎖定：

- account：5 次/15 分 → 15 分；10 次/1 時 → 30 分；15 次/24 時 → 1 時
- ip：10 次/1 分 → 1 分；30 次/15 分 → 15 分

只計失敗；成功登入會清除帳號紀錄，但不清 IP（避免用已知密碼重置）。
所有查詢／寫入失敗皆 fail-soft：log warning 後讓登入流程繼續，避免資料庫
異常時整個登入功能變成 500。
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import _utcnow
from app.models.login_attempt import LoginAttempt

logger = logging.getLogger(__name__)

Kind = Literal["account", "ip"]


@dataclass(frozen=True)
class LockoutTier:
    threshold: int
    window: timedelta
    lock: timedelta


#: 帳號分級；順序由短窗到長窗。
ACCOUNT_TIERS: tuple[LockoutTier, ...] = (
    LockoutTier(threshold=5, window=timedelta(minutes=15), lock=timedelta(minutes=15)),
    LockoutTier(threshold=10, window=timedelta(hours=1), lock=timedelta(minutes=30)),
    LockoutTier(threshold=15, window=timedelta(hours=24), lock=timedelta(hours=1)),
)

#: 來源 IP 分級；第一級先擋高頻爆發，第二級擋持續噴射。
IP_TIERS: tuple[LockoutTier, ...] = (
    LockoutTier(threshold=10, window=timedelta(minutes=1), lock=timedelta(minutes=1)),
    LockoutTier(threshold=30, window=timedelta(minutes=15), lock=timedelta(minutes=15)),
)

#: 只保留 24 小時；每次寫入順便清理，避免表無限成長。
RETENTION = timedelta(hours=24)

ACCOUNT_MAX_WINDOW = max(tier.window for tier in ACCOUNT_TIERS)
IP_MAX_WINDOW = max(tier.window for tier in IP_TIERS)


@dataclass(frozen=True)
class ThrottleStatus:
    blocked: bool
    retry_after_seconds: int = 0


ALLOWED = ThrottleStatus(blocked=False)


def key_hash(kind: Kind, value: str) -> str:
    """以 JWT secret 做 HMAC-SHA256，回傳 64 字元 hex。"""
    secret = get_settings().jwt_secret.encode("utf-8")
    message = f"{kind}:{value}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _as_utc(value: datetime) -> datetime:
    """SQLite 會回傳 naive datetime；一律視為 UTC。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _account_value(username: str) -> str:
    return username.strip()


def _ip_value(ip: str) -> str:
    return ip.strip() or "unknown"


async def _load_timestamps(
    session: AsyncSession,
    *,
    kind: Kind,
    value: str,
    since: datetime,
) -> list[datetime]:
    stmt = (
        select(LoginAttempt.created_at)
        .where(
            LoginAttempt.kind == kind,
            LoginAttempt.key_hash == key_hash(kind, value),
            LoginAttempt.created_at >= since,
        )
        .order_by(LoginAttempt.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_as_utc(row) for row in rows]


def _blocked_until(
    timestamps: list[datetime],
    tier: LockoutTier,
    now: datetime,
) -> datetime | None:
    """回傳此分級的解鎖時間；未達門檻或已解鎖 → None。

    `timestamps` 必須新到舊排序。以時間窗內最新一次失敗起算鎖定，
    避免慢速噴射（10 次分散在 1 小時）因為第 N 新太舊而提前解鎖。
    """
    cutoff = now - tier.window
    recent = [stamp for stamp in timestamps if stamp >= cutoff]
    if len(recent) < tier.threshold:
        return None
    until = recent[0] + tier.lock
    return until if until > now else None


def _max_blocked_until(
    timestamps: list[datetime],
    tiers: tuple[LockoutTier, ...],
    now: datetime,
) -> datetime | None:
    untils = [
        until
        for tier in tiers
        if (until := _blocked_until(timestamps, tier, now)) is not None
    ]
    return max(untils) if untils else None


async def _safe_rollback(session: AsyncSession) -> None:
    try:
        await session.rollback()
    except Exception:  # noqa: BLE001 — rollback 失敗不應蓋掉原始錯誤
        logger.warning("login throttle rollback failed", exc_info=True)


async def check(
    session: AsyncSession,
    *,
    username: str,
    ip: str,
) -> ThrottleStatus:
    """檢查帳號與 IP 是否被鎖；任何例外皆 fail-open。"""
    try:
        now = _utcnow()
        account_timestamps = await _load_timestamps(
            session,
            kind="account",
            value=_account_value(username),
            since=now - ACCOUNT_MAX_WINDOW,
        )
        ip_timestamps = await _load_timestamps(
            session,
            kind="ip",
            value=_ip_value(ip),
            since=now - IP_MAX_WINDOW,
        )
    except Exception:  # noqa: BLE001 — 可用性優先，不讓節流查詢造成登入 500
        logger.warning("login throttle check failed", exc_info=True)
        await _safe_rollback(session)
        return ALLOWED

    untils = [
        until
        for until in (
            _max_blocked_until(account_timestamps, ACCOUNT_TIERS, now),
            _max_blocked_until(ip_timestamps, IP_TIERS, now),
        )
        if until is not None
    ]
    if not untils:
        return ALLOWED

    retry_after = max(1, math.ceil((max(untils) - now).total_seconds()))
    return ThrottleStatus(blocked=True, retry_after_seconds=retry_after)


async def _persist_failure(
    session: AsyncSession,
    *,
    username: str,
    ip: str,
    now: datetime,
) -> None:
    session.add_all(
        [
            LoginAttempt(
                kind="account",
                key_hash=key_hash("account", _account_value(username)),
                created_at=now,
            ),
            LoginAttempt(
                kind="ip",
                key_hash=key_hash("ip", _ip_value(ip)),
                created_at=now,
            ),
        ]
    )
    await session.execute(
        delete(LoginAttempt).where(LoginAttempt.created_at < now - RETENTION)
    )
    await session.commit()


async def record_failure(
    session: AsyncSession,
    *,
    username: str,
    ip: str,
) -> None:
    """記錄一次失敗；例外只 log，不影響原本的 401。"""
    try:
        await _persist_failure(
            session,
            username=username,
            ip=ip,
            now=_utcnow(),
        )
    except Exception:  # noqa: BLE001 — 節流寫入失敗不應讓登入回 500
        logger.warning("login throttle write failed", exc_info=True)
        await _safe_rollback(session)


async def reset_account(session: AsyncSession, *, username: str) -> None:
    """成功登入後清除該帳號的失敗紀錄；不清 IP。"""
    try:
        await session.execute(
            delete(LoginAttempt).where(
                LoginAttempt.kind == "account",
                LoginAttempt.key_hash == key_hash(
                    "account", _account_value(username)
                ),
            )
        )
        await session.commit()
    except Exception:  # noqa: BLE001 — 清除失敗不應影響登入成功
        logger.warning("login throttle reset failed", exc_info=True)
        await _safe_rollback(session)
