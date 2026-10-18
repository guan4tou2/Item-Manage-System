import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import type { ReportRead } from "@/lib/api/reports"
import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"

import { ReportCard } from "./report-card"

function makeReport(overrides: Partial<ReportRead["payload"]> = {}): ReportRead {
  return {
    id: "r1",
    period: "2026-09",
    generated_at: "2026-10-01T00:05:00Z",
    payload: {
      version: 1,
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
        loans_out: 1,
        loans_returned: 0,
        loans_overdue: 0,
      },
      expiry: { expiring_soon: 1, expired: 0 },
      valuation: {
        start: "1200.00",
        end: "1500.00",
        delta: "300.00",
        unpriced_items: 0,
      },
      top_categories: [],
      top_locations: [],
      has_activity: true,
      ...overrides,
    },
  }
}

function renderCard(report: ReportRead, locale = "en") {
  return render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "zh-TW" ? zhMessages : enMessages}
    >
      <ReportCard report={report} />
    </NextIntlClientProvider>,
  )
}

describe("ReportCard", () => {
  it("renders the period, summary and detail link", () => {
    renderCard(makeReport())

    expect(screen.getByText("September 2026")).toBeInTheDocument()
    expect(screen.getByTestId("report-summary")).toHaveTextContent(
      "42 items · 2 added · 3 used · value NT$300",
    )
    expect(screen.getByRole("link")).toHaveAttribute("href", "/reports/r1")
  })

  it("shows the localized period in zh-TW", () => {
    renderCard(makeReport(), "zh-TW")

    expect(screen.getByText("2026年9月")).toBeInTheDocument()
    expect(screen.getByTestId("report-summary")).toHaveTextContent("42 件")
  })

  it("badges a month without activity", () => {
    renderCard(makeReport({ has_activity: false }))

    expect(screen.getByText(enMessages.reports.noActivity)).toBeInTheDocument()
  })

  it("does not badge an active month", () => {
    renderCard(makeReport())

    expect(screen.queryByText(enMessages.reports.noActivity)).not.toBeInTheDocument()
  })

  it("renders the generated timestamp", () => {
    renderCard(makeReport())

    const generated = screen.getByTestId("report-generated-at")
    expect(generated).toHaveTextContent(/Generated/)
    expect(generated).toHaveTextContent(/2026/)
  })
})
