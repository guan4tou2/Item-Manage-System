"""全站「今天」的唯一來源：Asia/Taipei。

`days_left`／批次狀態／列表篩選／Phase 24 門檻判定一律使用本模組，
不得再散落 `date.today()`（避免 UTC 與台北日期的午夜錯位）。
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")

#: 「即將到期」門檻（列表篩選、badge 與批次狀態共用）
EXPIRING_SOON_DAYS = 7


def today_taipei(now: datetime | None = None) -> date:
    """Asia/Taipei 的今天。`now` 供測試注入（須為 aware datetime）。"""
    moment = now if now is not None else datetime.now(UTC)
    return moment.astimezone(TAIPEI).date()


def days_left(expiry_date: date, *, today: date | None = None) -> int:
    """距到期日天數；負數＝已過期。"""
    return (expiry_date - (today if today is not None else today_taipei())).days


def expiry_status(expiry_date: date | None, *, today: date | None = None) -> str:
    """`ok | expiring | expired`；無到期日視為 `ok`。"""
    if expiry_date is None:
        return "ok"
    remaining = days_left(expiry_date, today=today)
    if remaining < 0:
        return "expired"
    if remaining <= EXPIRING_SOON_DAYS:
        return "expiring"
    return "ok"
