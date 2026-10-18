"""月報伺服器端渲染（Phase 31）。

站內通知文字與 Email（plain text＋HTML）都由同一份 `ReportPayload` 產生；
語言依收件者 `preferences.language`。HTML 內所有使用者可控字串一律 escape。

Email 契約：zh-TW／en、plain-text fallback、CSV 附件不在本期。
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from html import escape

from app.clock import TAIPEI
from app.schemas.reports import ReportPayload

EM_DASH = "—"

MONTHS_EN = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

CURRENCY_SYMBOLS = {
    "TWD": "NT$",
    "USD": "US$",
    "EUR": "€",
    "JPY": "¥",
    "CNY": "CN¥",
    "HKD": "HK$",
}

TEXT: dict[str, dict[str, str]] = {
    "zh-TW": {
        "htmlLang": "zh-Hant-TW",
        "title": "月報：{period}",
        "subject": "月報已生成：{period}",
        "inventory": "庫存現況",
        "items": "物品",
        "quantity": "總數量",
        "activity": "本月動態",
        "created": "新增",
        "deleted": "刪除",
        "qtyIn": "入庫",
        "qtyOut": "消耗",
        "loansOut": "借出",
        "loansReturned": "歸還",
        "loansOverdue": "逾期未還",
        "expiry": "到期狀態（月底）",
        "expiring": "30 天內到期",
        "expired": "已過期",
        "valuation": "庫存估值",
        "start": "月初",
        "end": "月末",
        "delta": "變化",
        "unpriced": "{count} 件未設定成本",
        "topCategories": "熱門分類",
        "topLocations": "熱門位置",
        "uncategorized": "未分類",
        "unassigned": "未指定",
        "noActivity": "本月無動態",
        "generated": "產生時間",
        "view": "查看完整報表",
        "count": "{label}（{count}）",
        "itemsUnit": "{count} 件",
        "notificationBody": "新增 {created} 件 · 消耗 {used} 件 · 估值 {value}",
    },
    "en": {
        "htmlLang": "en",
        "title": "Monthly report: {period}",
        "subject": "Your {period} report is ready",
        "inventory": "Inventory snapshot",
        "items": "Items",
        "quantity": "Total quantity",
        "activity": "This month",
        "created": "Added",
        "deleted": "Deleted",
        "qtyIn": "Stock in",
        "qtyOut": "Used",
        "loansOut": "Lent",
        "loansReturned": "Returned",
        "loansOverdue": "Overdue",
        "expiry": "Expiry at month end",
        "expiring": "Expiring in 30 days",
        "expired": "Expired",
        "valuation": "Inventory value",
        "start": "Start of month",
        "end": "End of month",
        "delta": "Change",
        "unpriced": "{count} items without cost",
        "topCategories": "Top categories",
        "topLocations": "Top locations",
        "uncategorized": "Uncategorized",
        "unassigned": "Unassigned",
        "noActivity": "No activity this month",
        "generated": "Generated",
        "view": "View the full report",
        "count": "{label} ({count})",
        "itemsUnit": "{count} items",
        "notificationBody": "{created} added · {used} used · value {value}",
    },
}


def _lang(language: str) -> str:
    return language if language in TEXT else "zh-TW"


def _t(language: str) -> dict[str, str]:
    return TEXT[_lang(language)]


def period_label(period: str, language: str) -> str:
    year, month = (int(part) for part in period.split("-"))
    if _lang(language) == "en":
        return f"{MONTHS_EN[month - 1]} {year}"
    return f"{year} 年 {month} 月"


def money(value: str | None, currency: str, language: str) -> str:  # noqa: ARG001
    """與 Web `formatCurrency` 對齊：固定符號、整數 0 位、有小數 2 位。"""
    if value is None or value == "":
        return EM_DASH
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return EM_DASH

    digits = 0 if currency == "JPY" or amount == amount.to_integral_value() else 2
    sign = "-" if amount < 0 else ""
    symbol = CURRENCY_SYMBOLS.get(currency, f"{currency} ")
    return f"{sign}{symbol}{abs(amount):,.{digits}f}"


def _generated_label(value: datetime) -> str:
    if value.tzinfo is None:  # SQLite 回 naive；一律視為 UTC
        value = value.replace(tzinfo=UTC)
    return value.astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M")


def _count_text(t: dict[str, str], count: int) -> str:
    return t["itemsUnit"].format(count=count)


def notification_text(payload: ReportPayload, language: str) -> tuple[str, str]:
    """站內通知（與 Email subject 共用）的 title／body。"""
    t = _t(language)
    label = period_label(payload.period, language)
    title = t["subject"].format(period=label)
    body = t["notificationBody"].format(
        created=payload.activity.items_created,
        used=payload.activity.quantity_out,
        value=money(payload.valuation.end, payload.currency, language),
    )
    return title, body


def _bucket_lines(
    buckets: list, empty_label: str, language: str
) -> list[str]:
    t = _t(language)
    lines = []
    for bucket in buckets:
        label = bucket.label if bucket.label is not None else empty_label
        lines.append(t["count"].format(label=label, count=bucket.count))
    return lines


def render_text(payload: ReportPayload, language: str, link: str) -> str:
    t = _t(language)
    label = period_label(payload.period, language)
    lines = [t["title"].format(period=label), ""]
    if not payload.has_activity:
        lines += [t["noActivity"], ""]

    colon = "：" if _lang(language) == "zh-TW" else ": "
    lines += [
        t["inventory"],
        f"- {t['items']}{colon}{payload.totals.item_count}",
        f"- {t['quantity']}{colon}{payload.totals.quantity}",
        "",
        t["activity"],
    ]
    activity = [
        (t["created"], payload.activity.items_created),
        (t["deleted"], payload.activity.items_deleted),
        (t["qtyIn"], payload.activity.quantity_in),
        (t["qtyOut"], payload.activity.quantity_out),
        (t["loansOut"], payload.activity.loans_out),
        (t["loansReturned"], payload.activity.loans_returned),
        (t["loansOverdue"], payload.activity.loans_overdue),
    ]
    lines += [f"- {name}{colon}{value}" for name, value in activity]

    lines += [
        "",
        t["expiry"],
        f"- {t['expiring']}{colon}{payload.expiry.expiring_soon}",
        f"- {t['expired']}{colon}{payload.expiry.expired}",
        "",
        t["valuation"],
        f"- {t['start']}{colon}{money(payload.valuation.start, payload.currency, language)}",
        f"- {t['end']}{colon}{money(payload.valuation.end, payload.currency, language)}",
        f"- {t['delta']}{colon}{money(payload.valuation.delta, payload.currency, language)}",
    ]
    if payload.valuation.unpriced_items:
        lines.append(
            f"- {t['unpriced'].format(count=payload.valuation.unpriced_items)}"
        )

    for heading, buckets, empty in (
        (t["topCategories"], payload.top_categories, t["uncategorized"]),
        (t["topLocations"], payload.top_locations, t["unassigned"]),
    ):
        lines += ["", heading]
        bucket_lines = _bucket_lines(buckets, empty, language)
        lines += [f"- {line}" for line in bucket_lines] or [f"- {EM_DASH}"]

    lines += [
        "",
        f"{t['generated']}{colon}{_generated_label(payload.generated_at)}",
        f"{t['view']}{colon}{link}",
    ]
    return "\n".join(lines)


def _html_rows(rows: list[tuple[str, str]]) -> str:
    return "".join(
        "<tr>"
        f'<td style="padding:4px 0;color:#6b7280;">{escape(str(key))}</td>'
        f'<td align="right" style="padding:4px 4px 4px 16px;font-weight:600;color:#111827;">'
        f"{escape(str(value))}</td>"
        "</tr>"
        for key, value in rows
    )


def _html_section(title: str, rows: list[tuple[str, str]]) -> str:
    return (
        '<section style="margin:0 0 20px;">'
        f'<h2 style="margin:0 0 8px;font-size:15px;color:#111827;">{escape(title)}</h2>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="font-size:14px;border-collapse:collapse;">'
        f"{_html_rows(rows)}"
        "</table></section>"
    )


def _html_list(title: str, lines: list[str]) -> str:
    body = "".join(
        f'<li style="margin:2px 0;">{escape(line)}</li>' for line in lines
    )
    if not body:
        body = f'<li style="margin:2px 0;color:#6b7280;">{EM_DASH}</li>'
    return (
        '<section style="margin:0 0 20px;">'
        f'<h2 style="margin:0 0 8px;font-size:15px;color:#111827;">{escape(title)}</h2>'
        '<ul style="margin:0;padding-left:20px;font-size:14px;color:#111827;">'
        f"{body}</ul></section>"
    )


def render_html(payload: ReportPayload, language: str, link: str) -> str:
    t = _t(language)
    lang = _lang(language)
    label = period_label(payload.period, lang)
    title = t["title"].format(period=label)
    colon = "：" if lang == "zh-TW" else ": "

    def money_text(value: str | None) -> str:
        return money(value, payload.currency, lang)

    activity_rows = [
        (t["created"], _count_text(t, payload.activity.items_created)),
        (t["deleted"], _count_text(t, payload.activity.items_deleted)),
        (t["qtyIn"], str(payload.activity.quantity_in)),
        (t["qtyOut"], str(payload.activity.quantity_out)),
        (t["loansOut"], str(payload.activity.loans_out)),
        (t["loansReturned"], str(payload.activity.loans_returned)),
        (t["loansOverdue"], str(payload.activity.loans_overdue)),
    ]
    valuation_rows = [
        (t["start"], money_text(payload.valuation.start)),
        (t["end"], money_text(payload.valuation.end)),
        (t["delta"], money_text(payload.valuation.delta)),
    ]
    if payload.valuation.unpriced_items:
        valuation_rows.append(
            ("", t["unpriced"].format(count=payload.valuation.unpriced_items))
        )

    no_activity = (
        f'<p style="margin:0 0 16px;padding:10px 12px;background:#f3f4f6;'
        f'border-radius:6px;color:#374151;font-size:14px;">{escape(t["noActivity"])}</p>'
        if not payload.has_activity
        else ""
    )

    category_lines = _bucket_lines(
        payload.top_categories, t["uncategorized"], lang
    )
    location_lines = _bucket_lines(
        payload.top_locations, t["unassigned"], lang
    )

    return f"""<!DOCTYPE html>
<html lang="{t['htmlLang']}">
<head><meta charset="utf-8"><title>{escape(title)}</title></head>
<body style="margin:0;padding:24px;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#111827;">
  <div style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:28px;">
    <p style="margin:0 0 4px;font-size:13px;color:#6b7280;">{escape(t["inventory"])}</p>
    <h1 style="margin:0 0 20px;font-size:22px;">{escape(title)}</h1>
    {no_activity}
    {_html_section(t["inventory"], [
        (t["items"], t["itemsUnit"].format(count=payload.totals.item_count)),
        (t["quantity"], str(payload.totals.quantity)),
    ])}
    {_html_section(t["activity"], activity_rows)}
    {_html_section(t["expiry"], [
        (t["expiring"], str(payload.expiry.expiring_soon)),
        (t["expired"], str(payload.expiry.expired)),
    ])}
    {_html_section(t["valuation"], valuation_rows)}
    {_html_list(t["topCategories"], category_lines)}
    {_html_list(t["topLocations"], location_lines)}
    <p style="margin:24px 0 0;padding-top:16px;border-top:1px solid #e5e7eb;font-size:13px;color:#6b7280;">
      {escape(t["generated"])}{colon}{escape(_generated_label(payload.generated_at))}<br>
      <a href="{escape(link, quote=True)}" style="color:#2563eb;">{escape(t["view"])}</a>
    </p>
  </div>
</body>
</html>"""
