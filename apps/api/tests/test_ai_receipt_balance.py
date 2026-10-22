"""Phase 38 T1.2：收據算術驗證（純函式）。

移植自 itemly（MIT）的收據驗證語意，改寫為 Python：

    calculated_total = Σ item.subtotal − receipt_discount + tax_total + shipping

- `balanced`：|calculated_total − total| < 0.01
- `discrepancy`：有差額（保留正負號：total − calculated_total）
- `incomplete`：缺總額／有缺價品項／幣別未知（XXX）→ **無法判斷**
- `unknown`：舊資料（無總額與品項）→ 不顯示判讀
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.receipt_balance import (
    UNKNOWN_CURRENCY,
    BalanceStatus,
    compute_balance,
)

D = Decimal


def _item(name: str, subtotal: str | None, unit_price: str | None = None) -> dict:
    return {
        "name": name,
        "subtotal": D(subtotal) if subtotal is not None else None,
        "unit_price": D(unit_price) if unit_price is not None else None,
    }


def test_balanced_when_totals_match():
    result = compute_balance(
        total=D("135.00"),
        items=[_item("甲", "100.00", "50.00"), _item("乙", "40.00", "40.00")],
        discount=D("10.00"),
        tax=D("5.00"),
        shipping=None,
        currency="TWD",
    )
    assert result.status == "balanced"
    assert result.calculated_total == D("135.00")
    assert result.discrepancy == D("0.00")
    assert result.missing_price_count == 0


def test_discrepancy_when_amounts_differ():
    result = compute_balance(
        total=D("150.00"),
        items=[_item("甲", "100.00", "50.00"), _item("乙", "40.00", "40.00")],
        discount=None,
        tax=None,
        shipping=None,
        currency="TWD",
    )
    assert result.status == "discrepancy"
    assert result.calculated_total == D("140.00")
    assert result.discrepancy == D("10.00")


def test_discrepancy_keeps_sign():
    """收據總額低於算術值 → 差額為負（超付情境）。"""
    result = compute_balance(
        total=D("130.00"),
        items=[_item("甲", "140.00", "140.00")],
        discount=None,
        tax=None,
        shipping=None,
        currency="TWD",
    )
    assert result.status == "discrepancy"
    assert result.discrepancy == D("-10.00")


def test_shipping_and_tax_are_added():
    result = compute_balance(
        total=D("150.00"),
        items=[_item("甲", "140.00", "140.00")],
        discount=None,
        tax=D("5.00"),
        shipping=D("5.00"),
        currency="TWD",
    )
    assert result.calculated_total == D("150.00")
    assert result.status == "balanced"


def test_missing_price_item_is_excluded_and_counted():
    """缺單價且缺小計的品項不參與合計，並計入待補價數。"""
    result = compute_balance(
        total=D("100.00"),
        items=[_item("甲", "100.00", "50.00"), _item("乙", None, None)],
        discount=None,
        tax=None,
        shipping=None,
        currency="TWD",
    )
    assert result.missing_price_count == 1
    assert result.calculated_total == D("100.00")
    # 有缺價品項 → 無法判斷（不可宣稱平衡）
    assert result.status == "incomplete"


def test_incomplete_when_total_missing():
    result = compute_balance(
        total=None,
        items=[_item("甲", "100.00", "50.00")],
        discount=None,
        tax=None,
        shipping=None,
        currency="TWD",
    )
    assert result.status == "incomplete"
    assert result.calculated_total == D("100.00")
    assert result.discrepancy is None


def test_incomplete_when_currency_unknown():
    result = compute_balance(
        total=D("100.00"),
        items=[_item("甲", "100.00", "50.00")],
        discount=None,
        tax=None,
        shipping=None,
        currency=UNKNOWN_CURRENCY,
    )
    assert result.status == "incomplete"
    assert result.currency_unknown is True


def test_unknown_when_nothing_extracted():
    result = compute_balance(
        total=None,
        items=[],
        discount=None,
        tax=None,
        shipping=None,
        currency="TWD",
    )
    assert result.status == "unknown"
    assert result.calculated_total is None


def test_decimal_precision_avoids_false_difference():
    """0.1 + 0.2 類情境不得被判成差額（全程 Decimal）。"""
    result = compute_balance(
        total=D("0.30"),
        items=[_item("甲", "0.10", "0.10"), _item("乙", "0.20", "0.20")],
        discount=None,
        tax=None,
        shipping=None,
        currency="TWD",
    )
    assert result.calculated_total == D("0.30")
    assert result.status == "balanced"


def test_item_subtotal_falls_back_to_unit_price_times_quantity():
    """品項缺小計但有單價與數量 → 以單價 × 數量計算。"""
    result = compute_balance(
        total=D("100.00"),
        items=[{"name": "甲", "subtotal": None, "unit_price": D("50.00"), "quantity": 2}],
        discount=None,
        tax=None,
        shipping=None,
        currency="TWD",
    )
    assert result.calculated_total == D("100.00")
    assert result.missing_price_count == 0


def test_balance_status_literal_values():
    assert set(BalanceStatus.__args__) == {
        "balanced",
        "discrepancy",
        "incomplete",
        "unknown",
    }
