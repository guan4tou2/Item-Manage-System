"""月報生成（Phase 31）。

- 期間固定 Asia/Taipei 的完整月份；時間欄位以 UTC 半開區間查詢
- 可見範圍沿用 `visibility_service.visible_item_owner_ids()`（本人＋同群組）
- `build_payload` 只讀不寫；job（T1.7）負責冪等落地與交付
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import TAIPEI
from app.config import get_settings
from app.models.user import User
from app.repositories import locations_repository, reports_repository
from app.schemas.reports import (
    ReportActivity,
    ReportBucket,
    ReportExpiry,
    ReportPayload,
    ReportTotals,
    ReportValuation,
)
from app.services import (
    external_notifications,
    jobs_service,
    notification_prefs,
    notifications_service,
    preferences_service,
    report_render,
    visibility_service,
)

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


def _as_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


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

    expiry_soon, expired = await reports_repository.expiry_counts(
        session,
        owner_ids,
        period_end=period.end,
        horizon_days=EXPIRING_HORIZON_DAYS,
    )
    loans_out, loans_returned, loans_overdue = (
        await reports_repository.loan_counts(
            session,
            owner_ids,
            start=period.start_utc,
            end=period.end_utc,
            period_end=period.end,
        )
    )
    end_value, created_value, deleted_value, log_delta_value, unpriced = (
        await reports_repository.valuation_parts(
            session, owner_ids, start=period.start_utc, end=period.end_utc
        )
    )
    end_dec = _as_decimal(end_value)
    start_dec = (
        end_dec
        - _as_decimal(created_value)
        + _as_decimal(deleted_value)
        - _as_decimal(log_delta_value)
    )
    valuation = ReportValuation(
        start=_money(start_dec),
        end=_money(end_dec),
        delta=_money(end_dec - start_dec),
        unpriced_items=unpriced,
    )

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
        version=1,
        period=period.key,
        timezone="Asia/Taipei",
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


# ---------- job（report.monthly） ----------------------------------------


async def _deliver_report(
    session: AsyncSession,
    *,
    user_id: UUID,
    report_id: UUID,
    payload: ReportPayload,
    language: str,
) -> bool:
    """站內通知＋HTML Email。回傳是否有任一管道實際成立（emit 失敗視為未成立）。"""
    user = await session.get(User, user_id)
    if user is None:
        return False

    title, body = report_render.notification_text(payload, language)
    link = f"/reports/{report_id}"
    absolute = f"{get_settings().public_web_url.rstrip('/')}{link}"

    delivered = False
    if user.email and await notification_prefs.is_enabled(
        session, user_id, type="report_ready", channel="email"
    ):
        text = report_render.render_text(payload, language, absolute)
        html = report_render.render_html(payload, language, absolute)
        delivered = await external_notifications.deliver_email(
            user.email, title, text, html=html
        )

    notification = await notifications_service.emit(
        session,
        user_id=user_id,
        type="report_ready",
        title=title,
        body=body,
        link=link,
        exclude_channels=frozenset({"email"}),
    )
    return delivered or notification is not None


async def generate_monthly(
    session: AsyncSession, today: date
) -> jobs_service.JobResult:
    """`report.monthly`：為每位合格使用者生成上一個完整月的報表。

    - 資格：is_active ＋ 月報開關開啟 ＋ 至少 1 件可見（未刪除）物品
    - 空動態月仍建立列（站內留痕），但不通知、不寄信
    - 已存在同 `(user_id, period)` → 跳過（冪等）
    - 每位使用者獨立 commit；失敗 rollback 並記入 `errors`，不阻斷其他人
    """
    period = previous_period(today)
    generated_at = datetime.now(UTC)
    result = jobs_service.JobResult()

    user_ids = list(
        (
            await session.execute(
                select(User.id).where(User.is_active.is_(True))
            )
        ).scalars()
    )

    for user_id in user_ids:
        try:
            prefs = await preferences_service.get_preferences(
                session, user_id=user_id
            )
            if not prefs.report_monthly_enabled:
                continue
            owner_ids = await visibility_service.visible_item_owner_ids(
                session, user_id
            )
            if not await reports_repository.has_visible_items(session, owner_ids):
                continue
            existing = await reports_repository.get_by_user_period(
                session, user_id, period.key
            )
            if existing is not None:
                continue

            payload = await build_payload(
                session,
                user_id=user_id,
                period=period,
                generated_at=generated_at,
                currency=prefs.currency,
            )
            row = await reports_repository.create(
                session,
                user_id=user_id,
                period=period.key,
                payload=payload.model_dump(mode="json"),
                generated_at=generated_at,
            )
            await session.commit()
            result.processed += 1

            if payload.has_activity and await _deliver_report(
                session,
                user_id=user_id,
                report_id=row.id,
                payload=payload,
                language=prefs.language,
            ):
                await session.commit()
                result.emitted += 1
        except Exception as exc:  # noqa: BLE001 — 單一使用者失敗不阻斷整批
            await session.rollback()
            result.errors.append(f"{user_id}: {type(exc).__name__}: {exc}")

    return result


jobs_service.register(
    jobs_service.JobSpec(name="report.monthly", run=generate_monthly)
)
