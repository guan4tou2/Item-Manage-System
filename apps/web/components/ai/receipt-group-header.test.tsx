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
