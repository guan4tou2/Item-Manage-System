import { render, screen, within } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import type { ReportPayload } from "@/lib/api/reports"
import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"

import { ReportSummary } from "./report-summary"

function makePayload(overrides: Partial<ReportPayload> = {}): ReportPayload {
  return {
    version: 1,
    kind: "monthly",
    period: "2026-09",
    timezone: "Asia/Taipei",
    period_start: "2026-09-01",
    period_end: "2026-09-30",
    generated_at: "2026-10-01T00:05:00Z",
    currency: "TWD",
    totals: { item_count: 42, quantity: 123 },
    activity: {
      items_created: 2,
      items_deleted: 1,
      quantity_in: 5,
      quantity_out: 3,
      loans_out: 4,
      loans_returned: 2,
      loans_overdue: 1,
    },
    expiry: { expiring_soon: 3, expired: 2 },
    valuation: {
      start: "1200.00",
      end: "1500.00",
      delta: "300.00",
      unpriced_items: 0,
    },
    top_categories: [
      { label: "食品", count: 12 },
      { label: null, count: 3 },
    ],
    top_locations: [{ label: null, count: 4 }],
    has_activity: true,
    ...overrides,
  }
}

function makeWeeklyPayload(
  overrides: Partial<ReportPayload> = {},
): ReportPayload {
  return makePayload({
    kind: "weekly",
    period: "2026-W42",
    period_start: "2026-10-12",
    period_end: "2026-10-18",
    ...overrides,
  })
}

function renderSummary(payload: ReportPayload, locale = "en", heading = "September 2026 report") {
  return render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "zh-TW" ? zhMessages : enMessages}
    >
      <ReportSummary payload={payload} heading={heading} />
    </NextIntlClientProvider>,
  )
}

describe("ReportSummary", () => {
  it("renders the inventory, expiry and activity numbers", () => {
    renderSummary(makePayload())

    const inventory = screen.getByTestId("report-inventory")
    expect(within(inventory).getByText("42")).toBeInTheDocument()
    expect(within(inventory).getByText("123")).toBeInTheDocument()

    const expiry = screen.getByTestId("report-expiry")
    expect(within(expiry).getByText("3")).toBeInTheDocument()
    expect(within(expiry).getByText("2")).toBeInTheDocument()

    const activity = screen.getByTestId("report-activity")
    expect(within(activity).getAllByText("1")).toHaveLength(2) // deleted + overdue
    expect(within(activity).getByText("5")).toBeInTheDocument() // stock in
    expect(within(activity).getByText("4")).toBeInTheDocument() // lent
  })

  it("shows a positive valuation delta with a plus sign", () => {
    renderSummary(makePayload())

    const delta = screen.getByTestId("report-valuation-delta")
    expect(delta).toHaveTextContent("+NT$300")
    expect(delta.className).toContain("emerald")
  })

  it("shows a negative valuation delta in destructive color", () => {
    renderSummary(
      makePayload({
        valuation: {
          start: "1500.00",
          end: "1200.00",
          delta: "-300.00",
          unpriced_items: 0,
        },
      }),
    )

    const delta = screen.getByTestId("report-valuation-delta")
    expect(delta).toHaveTextContent("-NT$300")
    expect(delta.className).toContain("text-destructive")
  })

  it("notes unpriced items only when some exist", () => {
    const { unmount } = renderSummary(
      makePayload({
        valuation: {
          start: "0.00",
          end: "0.00",
          delta: "0.00",
          unpriced_items: 5,
        },
      }),
    )
    expect(screen.getByTestId("report-unpriced")).toHaveTextContent(
      "5 items without cost",
    )
    unmount()

    renderSummary(makePayload())
    expect(screen.queryByTestId("report-unpriced")).not.toBeInTheDocument()
  })

  it("badges a month without activity", () => {
    renderSummary(makePayload({ has_activity: false }))

    expect(screen.getByText(enMessages.reports.noActivity)).toBeInTheDocument()
  })

  it("falls back to uncategorized and unassigned labels", () => {
    renderSummary(makePayload())

    const categories = screen.getByTestId("report-top-categories")
    expect(within(categories).getByText("食品")).toBeInTheDocument()
    expect(within(categories).getByText("3 items")).toBeInTheDocument()
    expect(within(categories).getByText("Uncategorized")).toBeInTheDocument()

    const locations = screen.getByTestId("report-top-locations")
    expect(within(locations).getByText("Unassigned")).toBeInTheDocument()
  })

  it("uses a mobile-first grid for the activity section", () => {
    renderSummary(makePayload())

    const content = screen.getByTestId("report-activity").querySelector(
      "[class*='grid-cols-2']",
    )
    expect(content?.className).toContain("grid-cols-2")
    expect(content?.className).toContain("sm:grid-cols-4")
  })

  it("renders zh-TW copy and heading", () => {
    renderSummary(makePayload(), "zh-TW", "2026年9月月報")

    expect(screen.getByRole("heading", { name: "2026年9月月報" })).toBeInTheDocument()
    expect(screen.getByTestId("report-valuation")).toHaveTextContent("庫存估值")
    expect(screen.getByTestId("report-top-categories")).toHaveTextContent("未分類")
  })

  it("uses weekly copy for a weekly payload", () => {
    renderSummary(
      makeWeeklyPayload(),
      "en",
      "Weekly report: Oct 12–18, 2026",
    )

    expect(
      screen.getByRole("heading", {
        name: "Weekly report: Oct 12–18, 2026",
      }),
    ).toBeInTheDocument()
    expect(screen.getByTestId("report-activity")).toHaveTextContent("This week")
    expect(screen.getByTestId("report-expiry")).toHaveTextContent(
      "Expiry at week end",
    )
    expect(screen.getByTestId("report-valuation")).toHaveTextContent(
      "Start of week",
    )
    expect(screen.getByTestId("report-valuation")).toHaveTextContent(
      "End of week",
    )
    expect(screen.getByTestId("report-activity")).not.toHaveTextContent(
      "This month",
    )
  })

  it("uses weekly copy in zh-TW", () => {
    renderSummary(
      makeWeeklyPayload(),
      "zh-TW",
      "2026 年 10 月 12–18 日 週報",
    )

    expect(screen.getByTestId("report-activity")).toHaveTextContent("本週動態")
    expect(screen.getByTestId("report-expiry")).toHaveTextContent(
      "到期狀態（週末）",
    )
    expect(screen.getByTestId("report-valuation")).toHaveTextContent("週初")
    expect(screen.getByTestId("report-valuation")).toHaveTextContent("週末")
    expect(screen.getByTestId("report-activity")).not.toHaveTextContent(
      "本月動態",
    )
  })

  it("badges a week without activity with weekly copy", () => {
    renderSummary(makeWeeklyPayload({ has_activity: false }))

    expect(
      screen.getByText(enMessages.reports.noActivityWeekly),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(enMessages.reports.noActivity),
    ).not.toBeInTheDocument()
  })
})
