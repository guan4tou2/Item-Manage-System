import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import type { ReceiptSnapshot } from "@/lib/api/ai-receipts"
import enMessages from "@/messages/en.json"

import { ReceiptGroupHeader } from "./receipt-group-header"

function snapshot(overrides: Partial<ReceiptSnapshot> = {}): ReceiptSnapshot {
  return {
    merchant: "PX Mart",
    purchased_at: "2026-10-18",
    currency: "TWD",
    total: "1250.00",
    item_total: "1240.00",
    discrepancy: "10.00",
    page_count: 2,
    truncated: false,
    ...overrides,
  } as ReceiptSnapshot
}

function renderHeader(props: {
  snapshot: ReceiptSnapshot | null
  itemCount: number
}) {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ReceiptGroupHeader {...props} />
    </NextIntlClientProvider>,
  )
}

describe("ReceiptGroupHeader", () => {
  it("shows merchant, date, page count, and item count", () => {
    renderHeader({ snapshot: snapshot(), itemCount: 3 })

    expect(screen.getByTestId("receipt-group-header")).toBeInTheDocument()
    expect(screen.getByText("PX Mart")).toBeInTheDocument()
    expect(screen.getByText("2026-10-18")).toBeInTheDocument()
    expect(screen.getByText("2 page(s)")).toBeInTheDocument()
    expect(screen.getByText("3 item(s)")).toBeInTheDocument()
  })

  it("warns about a mismatch between items and the receipt total", () => {
    renderHeader({ snapshot: snapshot(), itemCount: 2 })

    expect(
      screen.getByText(
        "Items total NT$1,240, receipt total NT$1,250 (difference NT$10)",
      ),
    ).toBeInTheDocument()
  })

  it("confirms when the totals match", () => {
    renderHeader({
      snapshot: snapshot({ total: "1240.00", discrepancy: "0.00" }),
      itemCount: 2,
    })

    expect(screen.getByText("Matches the receipt total")).toBeInTheDocument()
  })

  it("says so when the receipt has no total", () => {
    renderHeader({
      snapshot: snapshot({ total: null, item_total: "1240.00", discrepancy: null }),
      itemCount: 2,
    })

    expect(screen.getByText("The receipt has no total")).toBeInTheDocument()
  })

  // --- Phase 38：四態判讀＋算術拆解 -------------------------------------

  it("shows the arithmetic breakdown for a balanced receipt", () => {
    renderHeader({
      snapshot: snapshot({
        balance_status: "balanced",
        item_total: "323.00",
        total: "1250.00",
        discrepancy: "0.00",
        calculated_total: "1250.00",
        discount: "23.00",
        tax: "5.00",
        shipping: "950.00",
      }),
      itemCount: 2,
    })

    expect(screen.getByText("Matches the receipt total")).toBeInTheDocument()
    expect(
      screen.getByText(/Math: items NT\$323 − discount NT\$23/),
    ).toBeInTheDocument()
  })

  it("flags missing prices, unknown currency and uncertain fields", () => {
    renderHeader({
      snapshot: snapshot({
        balance_status: "incomplete",
        currency: "XXX",
        missing_price_count: 2,
        uncertain_fields: ["total", "currency"],
      }),
      itemCount: 3,
    })

    expect(screen.getByText("2 item(s) need a price")).toBeInTheDocument()
    expect(screen.getByText("Currency to confirm")).toBeInTheDocument()
    expect(screen.getByText("2 field(s) to confirm")).toBeInTheDocument()
  })

  it("keeps the legacy rendering for old snapshots", () => {
    renderHeader({ snapshot: snapshot(), itemCount: 2 })

    expect(
      screen.getByText(
        "Items total NT$1,240, receipt total NT$1,250 (difference NT$10)",
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Math: items NT\$1,240 −/)).not.toBeInTheDocument()
  })

  it("falls back for a missing merchant and date", () => {
    renderHeader({
      snapshot: snapshot({ merchant: null, purchased_at: null }),
      itemCount: 1,
    })

    expect(screen.getByText("Unlabeled merchant")).toBeInTheDocument()
    expect(screen.getByText("No date")).toBeInTheDocument()
  })

  it("renders a neutral header without a snapshot", () => {
    renderHeader({ snapshot: null, itemCount: 2 })

    expect(screen.getByTestId("receipt-group-header")).toBeInTheDocument()
    expect(screen.getByText("Unlabeled merchant")).toBeInTheDocument()
    expect(screen.getByText("2 item(s)")).toBeInTheDocument()
    expect(screen.queryByText("Matches the receipt total")).not.toBeInTheDocument()
  })
})
