from __future__ import annotations

from datetime import UTC, date, datetime

from app.schemas.reports import (
    ReportActivity,
    ReportBucket,
    ReportExpiry,
    ReportPayload,
    ReportTotals,
    ReportValuation,
)
from app.services import report_render

LINK = "http://localhost:3000/reports/abc"


def _payload(**overrides) -> ReportPayload:
    base = dict(
        period="2026-09",
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        generated_at=datetime(2026, 10, 1, 0, 5, tzinfo=UTC),
        currency="TWD",
        totals=ReportTotals(item_count=42, quantity=123),
        activity=ReportActivity(
            items_created=2,
            items_deleted=1,
            quantity_in=5,
            quantity_out=3,
            loans_out=4,
            loans_returned=2,
            loans_overdue=1,
        ),
        expiry=ReportExpiry(expiring_soon=3, expired=2),
        valuation=ReportValuation(
            start="1200.00", end="1500.00", delta="300.00", unpriced_items=2
        ),
        top_categories=[ReportBucket(label="食品", count=12)],
        top_locations=[ReportBucket(label="儲藏室 / 上層", count=8)],
        has_activity=True,
    )
    base.update(overrides)
    return ReportPayload(**base)


def test_period_label_bilingual():
    assert report_render.period_label("2026-09", "zh-TW") == "2026 年 9 月"
    assert report_render.period_label("2026-09", "en") == "September 2026"
    assert report_render.period_label("2026-01", "en") == "January 2026"


def test_money_matches_web_formatting():
    assert report_render.money("1200", "TWD", "zh-TW") == "NT$1,200"
    assert report_render.money("1200.5", "TWD", "en") == "NT$1,200.50"
    assert report_render.money("1200", "JPY", "en") == "¥1,200"
    assert report_render.money("-300", "TWD", "zh-TW") == "-NT$300"
    assert report_render.money(None, "TWD", "zh-TW") == "—"


def test_notification_text_bilingual():
    zh_title, zh_body = report_render.notification_text(_payload(), "zh-TW")
    assert "2026 年 9 月" in zh_title
    assert "月報" in zh_title
    assert "新增 2" in zh_body
    assert "消耗 3" in zh_body

    en_title, en_body = report_render.notification_text(_payload(), "en")
    assert "September 2026" in en_title
    assert "2 added" in en_body
    assert "3 used" in en_body


def test_render_text_contains_sections_and_link():
    text = report_render.render_text(_payload(), "zh-TW", LINK)

    assert "2026 年 9 月" in text
    assert "庫存現況" in text
    assert "本月動態" in text
    assert "庫存估值" in text
    assert "熱門分類" in text
    assert "食品（12）" in text
    assert LINK in text


def test_render_text_english():
    text = report_render.render_text(_payload(), "en", LINK)

    assert "September 2026" in text
    assert "Inventory snapshot" in text
    assert "Inventory value" in text
    assert "Top categories" in text


def test_render_text_empty_month_note():
    text = report_render.render_text(
        _payload(has_activity=False), "zh-TW", LINK
    )

    assert "本月無動態" in text


def test_render_html_escapes_user_labels():
    payload = _payload(
        top_categories=[ReportBucket(label="<script>alert(1)</script>", count=1)],
        top_locations=[ReportBucket(label="A & B", count=2)],
    )

    html = report_render.render_html(payload, "zh-TW", LINK)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html
    assert LINK in html
    assert "NT$1,500" in html


def test_render_html_bilingual_sections():
    html = report_render.render_html(_payload(), "en", LINK)

    assert "September 2026" in html
    assert "Inventory snapshot" in html
    assert "This month" in html
    assert "Expiring in 30 days" in html


def test_render_html_handles_naive_generated_at():
    payload = _payload(generated_at=datetime(2026, 10, 1, 0, 5))

    html = report_render.render_html(payload, "zh-TW", LINK)

    assert "2026-10-01" in html
