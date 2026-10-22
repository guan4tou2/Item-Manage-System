"""收據算術驗證（Phase 38；純函式、無 DB、無 LLM）。

移植自 [itemly](https://github.com/Kamitoad/itemly)（MIT）的收據驗證語意，
改寫為 Python／Decimal：

    calculated_total = Σ item.subtotal − receipt_discount + tax_total + shipping

狀態（`BalanceStatus`）：

| 狀態 | 意義 |
|------|------|
| `balanced` | 算術驗證通過（差額 < 0.01） |
| `discrepancy` | 有差額（`total − calculated_total`，保留正負號） |
| `incomplete` | 缺總額／有缺價品項／幣別未知 → **無法判斷** |
| `unknown` | 舊資料（無總額與品項）→ 不顯示判讀 |

- 全程 `Decimal`（`quantize(0.01)`），**不使用浮點**
- 缺價品項（缺小計且無法以單價 × 數量推得）→ 不參與合計，計入 `missing_price_count`
- 幣別未知用 ISO 4217 的 `XXX`（no-currency），**不猜測**幣別
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Optional

#: ISO 4217「無幣別」代碼（itemly 同款）：AI 讀不到幣別時使用，不猜測
UNKNOWN_CURRENCY = "XXX"

#: 差額門檻（絕對值小於此視為相符；沿用 Phase 33 的 0.01）
BALANCE_EPSILON = Decimal("0.01")

#: 金額精度（小數 2 位）
CENTS = Decimal("0.01")

BalanceStatus = Literal["balanced", "discrepancy", "incomplete", "unknown"]


def _money(value: Optional[Decimal]) -> Optional[Decimal]:
    """量化到 2 位小數（`None` 維持 `None`）。"""
    if value is None:
        return None
    return value.quantize(CENTS)


@dataclass(frozen=True)
class BalanceResult:
    """算術驗證結果（供快照與 UI 使用）。"""

    status: BalanceStatus
    #: Σ 品項小計 − 折扣 + 稅 + 運費（無法計算時為 `None`）
    calculated_total: Optional[Decimal] = None
    #: 收據總額 − 算術值（`balanced` 為 0.00；無法判斷時為 `None`）
    discrepancy: Optional[Decimal] = None
    #: 缺價（無法計算金額）的品項數
    missing_price_count: int = 0
    #: 幣別是否未知（`XXX`）
    currency_unknown: bool = False
    #: 品項小計合計（不含折扣／稅／運費）
    item_total: Optional[Decimal] = None


def _item_amount(item: dict[str, Any]) -> Optional[Decimal]:
    """品項金額：優先小計；缺小計則以單價 × 數量推得；皆缺 → `None`（缺價）。"""
    subtotal = item.get("subtotal")
    if isinstance(subtotal, Decimal):
        return subtotal
    unit_price = item.get("unit_price")
    quantity = item.get("quantity")
    if isinstance(unit_price, Decimal) and isinstance(quantity, int) and quantity > 0:
        return (unit_price * quantity).quantize(CENTS)
    return None


def compute_balance(
    *,
    total: Optional[Decimal],
    items: list[dict[str, Any]],
    discount: Optional[Decimal] = None,
    tax: Optional[Decimal] = None,
    shipping: Optional[Decimal] = None,
    currency: Optional[str] = None,
) -> BalanceResult:
    """計算收據對帳狀態（純函式；`items` 的金額欄位須為 `Decimal` 或 `None`）。"""
    currency_unknown = (currency or "").strip().upper() in ("", UNKNOWN_CURRENCY)

    item_total = Decimal("0.00")
    missing_price_count = 0
    priced_items = 0
    for item in items:
        amount = _item_amount(item)
        if amount is None:
            missing_price_count += 1
            continue
        priced_items += 1
        item_total += amount
    item_total = item_total.quantize(CENTS)

    if not items or (total is None and priced_items == 0):
        # 舊資料或未抽到任何金額 → 不顯示判讀
        return BalanceResult(
            status="unknown",
            calculated_total=None,
            discrepancy=None,
            missing_price_count=missing_price_count,
            currency_unknown=currency_unknown,
            item_total=None,
        )

    calculated = item_total
    if discount is not None:
        calculated -= discount
    if tax is not None:
        calculated += tax
    if shipping is not None:
        calculated += shipping
    calculated = calculated.quantize(CENTS)

    if total is None or missing_price_count > 0 or currency_unknown:
        return BalanceResult(
            status="incomplete",
            calculated_total=calculated,
            discrepancy=None,
            missing_price_count=missing_price_count,
            currency_unknown=currency_unknown,
            item_total=item_total,
        )

    discrepancy = _money(total - calculated)
    balanced = abs(discrepancy) < BALANCE_EPSILON
    return BalanceResult(
        status="balanced" if balanced else "discrepancy",
        calculated_total=calculated,
        discrepancy=Decimal("0.00") if balanced else discrepancy,
        missing_price_count=0,
        currency_unknown=False,
        item_total=item_total,
    )
