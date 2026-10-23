import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ReportRead } from "@/lib/api/reports"
import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"

import ReportsPage from "./page"

const mocks = vi.hoisted(() => ({
  refetch: vi.fn(),
  reports: {
    isLoading: false,
    isError: false,
    data: undefined as
      | { items: ReportRead[]; total: number; limit: number; offset: number }
      | undefined,
  },
  prefs: {
    data: {
      report_monthly_enabled: true,
      report_weekly_enabled: false,
    } as
      | {
          report_monthly_enabled: boolean
          report_weekly_enabled: boolean
        }
      | undefined,
  },
}))

vi.mock("@/lib/hooks/use-reports", () => ({
  useReports: () => ({ ...mocks.reports, refetch: mocks.refetch }),
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: () => mocks.prefs,
}))

function makeReport(
  overrides: Partial<ReportRead["payload"]> = {},
  kind: "monthly" | "weekly" = "monthly",
): ReportRead {
  const weekly = kind === "weekly"
  return {
    id: "r1",
    kind,
    period: weekly ? "2026-W42" : "2026-09",
    generated_at: "2026-10-01T00:05:00Z",
    payload: {
      version: 1,
      kind,
      period: weekly ? "2026-W42" : "2026-09",
      timezone: "Asia/Taipei",
      period_start: weekly ? "2026-10-12" : "2026-09-01",
      period_end: weekly ? "2026-10-18" : "2026-09-30",
      generated_at: "2026-10-01T00:05:00Z",
      currency: "TWD",
      totals: { item_count: 3, quantity: 9 },
      activity: {
        items_created: 1,
        items_deleted: 0,
        quantity_in: 4,
        quantity_out: 2,
        loans_out: 0,
        loans_returned: 0,
        loans_overdue: 0,
      },
      expiry: { expiring_soon: 0, expired: 0 },
      valuation: {
        start: "100.00",
        end: "200.00",
        delta: "100.00",
        unpriced_items: 0,
      },
      top_categories: [],
      top_locations: [],
      has_activity: true,
      ...overrides,
    },
  }
}

function renderPage(locale = "en") {
  return render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "zh-TW" ? zhMessages : enMessages}
    >
      <ReportsPage />
    </NextIntlClientProvider>,
  )
}

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.reports = {
      isLoading: false,
      isError: false,
      data: { items: [makeReport()], total: 1, limit: 20, offset: 0 },
    }
    mocks.prefs = {
      data: { report_monthly_enabled: true, report_weekly_enabled: false },
    }
  })

  it("renders the skeleton while loading", () => {
    mocks.reports = { isLoading: true, isError: false, data: undefined }

    renderPage()

    expect(screen.getByLabelText(enMessages.reports.loading)).toBeInTheDocument()
  })

  it("renders the period cards when reports exist", () => {
    renderPage()

    expect(
      screen.getByRole("heading", { name: enMessages.reports.title }),
    ).toBeInTheDocument()
    expect(screen.getByText("September 2026")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /September 2026/ })).toHaveAttribute(
      "href",
      "/reports/r1",
    )
  })

  it("renders a weekly card with its range", () => {
    mocks.reports = {
      isLoading: false,
      isError: false,
      data: {
        items: [makeReport({}, "weekly")],
        total: 1,
        limit: 20,
        offset: 0,
      },
    }

    renderPage()

    expect(screen.getByText(enMessages.reports.weeklyBadge)).toBeInTheDocument()
    expect(screen.getByText("Oct 12–18, 2026")).toBeInTheDocument()
  })

  it("renders the first-month empty state when there are no reports", () => {
    mocks.reports = {
      isLoading: false,
      isError: false,
      data: { items: [], total: 0, limit: 20, offset: 0 },
    }

    renderPage()

    expect(screen.getByText(enMessages.reports.empty.title)).toBeInTheDocument()
    expect(screen.getByText(enMessages.reports.empty.firstMonth)).toBeInTheDocument()
  })

  it("links to settings when both report kinds are disabled", () => {
    mocks.reports = {
      isLoading: false,
      isError: false,
      data: { items: [], total: 0, limit: 20, offset: 0 },
    }
    mocks.prefs = {
      data: { report_monthly_enabled: false, report_weekly_enabled: false },
    }

    renderPage()

    expect(screen.getByText(enMessages.reports.empty.disabled)).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: enMessages.reports.empty.openSettings }),
    ).toHaveAttribute("href", "/settings/reports")
  })

  it("shows the weekly-only empty state when monthly is off", () => {
    mocks.reports = {
      isLoading: false,
      isError: false,
      data: { items: [], total: 0, limit: 20, offset: 0 },
    }
    mocks.prefs = {
      data: { report_monthly_enabled: false, report_weekly_enabled: true },
    }

    renderPage()

    expect(
      screen.getByText(enMessages.reports.empty.weeklyOnly),
    ).toBeInTheDocument()
    expect(
      screen.getByText(enMessages.reports.empty.weeklyOnlyHint),
    ).toBeInTheDocument()
  })

  it("retries after a load error", async () => {
    const user = userEvent.setup()
    mocks.reports = { isLoading: false, isError: true, data: undefined }

    renderPage()

    expect(screen.getByText(enMessages.reports.loadError)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: enMessages.reports.retry }))
    expect(mocks.refetch).toHaveBeenCalledTimes(1)
  })

  it("renders zh-TW copy and period", () => {
    renderPage("zh-TW")

    expect(screen.getByRole("heading", { name: "報表" })).toBeInTheDocument()
    expect(screen.getByText("2026年9月")).toBeInTheDocument()
  })
})
