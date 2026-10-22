import { describe, expect, it } from "vitest"

import type { ReceiptSnapshot } from "@/lib/api/ai-receipts"

import { receiptBalanceOf } from "./receipts"

function snapshot(overrides: Partial<ReceiptSnapshot> = {}): ReceiptSnapshot {
  return {
    merchant: "全聯",
    purchased_at: "2026-10-18",
    currency: "TWD",
    total: "1250.00",
    item_total: "323.00",
    discrepancy: "927.00",
    page_count: 1,
    truncated: false,
    ...overrides,
  } as ReceiptSnapshot
}

describe("receiptBalanceOf", () => {
  it("新版快照：讀取 balance_status 與算術欄位", () => {
    const view = receiptBalanceOf(
      snapshot({
        balance_status: "discrepancy",
        subtotal: "323.00",
        discount: "23.00",
        tax: "0.00",
        shipping: "950.00",
        calculated_total: "1250.00",
        missing_price_count: 0,
        uncertain_fields: [],
      }),
    )

    expect(view.status).toBe("discrepancy")
    expect(view.evidence).toBe(true)
    expect(view.calculatedTotal).toBe("1250.00")
    expect(view.discount).toBe("23.00")
    expect(view.tax).toBe("0.00")
    expect(view.shipping).toBe("950.00")
    expect(view.missingPriceCount).toBe(0)
    expect(view.uncertainCount).toBe(0)
    expect(view.currencyUnknown).toBe(false)
  })

  it("舊快照（無 balance_status）→ 沿用舊判讀（evidence=false）", () => {
    const view = receiptBalanceOf(snapshot())

    expect(view.evidence).toBe(false)
    expect(view.status).toBe("discrepancy")
  })

  it("舊快照且缺總額 → unknown", () => {
    const view = receiptBalanceOf(snapshot({ total: null, discrepancy: null }))

    expect(view.status).toBe("unknown")
  })

  it("新版快照：幣別 XXX → currencyUnknown", () => {
    const view = receiptBalanceOf(
      snapshot({ balance_status: "incomplete", currency: "XXX" }),
    )

    expect(view.status).toBe("incomplete")
    expect(view.currencyUnknown).toBe(true)
  })

  it("新版快照：待補價與不確定欄位數", () => {
    const view = receiptBalanceOf(
      snapshot({
        balance_status: "incomplete",
        missing_price_count: 2,
        uncertain_fields: ["total", "currency"],
      }),
    )

    expect(view.missingPriceCount).toBe(2)
    expect(view.uncertainCount).toBe(2)
  })
})
