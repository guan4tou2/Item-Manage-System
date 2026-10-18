"""月報生成（Phase 31）。

- 期間固定 Asia/Taipei 的完整月份；時間欄位以 UTC 半開區間查詢
- 可見範圍沿用 `visibility_service.visible_item_owner_ids()`（本人＋同群組）
- `build_payload` 只讀不寫；job（T1.7）負責冪等落地與交付
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import TAIPEI
from app.repositories import locations_repository, reports_repository
from app.schemas.reports import (
    ReportActivity,
    ReportBucket,
    ReportExpiry,
    ReportPayload,
    ReportTotals,
    ReportValuation,
)
from app.services import visibility_service

#: 月報的「即將到期」視窗（與列表的 7 天不同；以期末為基準）
EXPIRING_HORIZON_DAYS = 30
#: 熱門分類／位置取前 N 名
TOP_BUCKETS = 3


@dataclass(frozen=True)
class Period:
    """一個完整月份（Asia/Taipei）。`end_utc` 為次月 1 日 00:00 TPE 的 UTC。"""

    key: str
    start: date
    end: date
    start_utc: datetime
    end_utc: datetime


def period_for(month_start: date) -> Period:
    """以某月任一天取得該月界線（統一正規化到 1 日）。"""
    start = month_start.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    next_start = end + timedelta(days=1)
    return Period(
        key=start.strftime("%Y-%m"),
        start=start,
        end=end,
        start_utc=datetime.combine(start, time.min, tzinfo=TAIPEI).astimezone(UTC),
        end_utc=datetime.combine(next_start, time.min, tzinfo=TAIPEI).astimezone(UTC),
    )


def previous_period(today: date) -> Period:
    """`today` 所屬月份的上一個完整月。"""
    first_of_this_month = today.replace(day=1)
    return period_for(first_of_this_month - timedelta(days=1))


async def build_payload(
    session: AsyncSession,
    *,
    user_id: UUID,
    period: Period,
    generated_at: datetime,
    currency: str,
) -> ReportPayload:
    owner_ids = sorted(
        await visibility_service.visible_item_owner_ids(session, user_id)
    )

    item_count, quantity = await reports_repository.totals(session, owner_ids)

    created = await reports_repository.items_created(
        session, owner_ids, start=period.start_utc, end=period.end_utc
    )
    deleted = await reports_repository.items_deleted(
        session, owner_ids, start=period.start_utc, end=period.end_utc
    )
    quantity_in, quantity_out = await reports_repository.quantity_deltas(
        session, owner_ids, start=period.start_utc, end=period.end_utc
    )

    # T1.3 補上估值／到期／借還；先以零值維持 payload 契約完整
    expiry_soon, expired = 0, 0
    loans_out, loans_returned, loans_overdue = 0, 0, 0
    valuation = ReportValuation()

    category_rows = await reports_repository.top_categories(
        session, owner_ids, limit=TOP_BUCKETS
    )
    location_rows = await reports_repository.top_locations(
        session, owner_ids, limit=TOP_BUCKETS
    )
    locations = []
    for owner_id in owner_ids:
        locations.extend(await locations_repository.fetch_all(session, owner_id))
    paths = locations_repository.paths_for(
        locations, [loc_id for loc_id, _ in location_rows if loc_id is not None]
    )

    activity = ReportActivity(
        items_created=created,
        items_deleted=deleted,
        quantity_in=quantity_in,
        quantity_out=quantity_out,
        loans_out=loans_out,
        loans_returned=loans_returned,
        loans_overdue=loans_overdue,
    )
    has_activity = any(
        value > 0
        for value in (
            activity.items_created,
            activity.items_deleted,
            activity.quantity_in,
            activity.quantity_out,
            activity.loans_out,
            activity.loans_returned,
        )
    )

    return ReportPayload(
        period=period.key,
        period_start=period.start,
        period_end=period.end,
        generated_at=generated_at,
        currency=currency,
        totals=ReportTotals(item_count=item_count, quantity=quantity),
        activity=activity,
        expiry=ReportExpiry(expiring_soon=expiry_soon, expired=expired),
        valuation=valuation,
        top_categories=[
            ReportBucket(label=label, count=count)
            for label, count in category_rows
        ],
        top_locations=[
            ReportBucket(label=paths.get(loc_id) if loc_id is not None else None, count=count)
            for loc_id, count in location_rows
        ],
        has_activity=has_activity,
    )
