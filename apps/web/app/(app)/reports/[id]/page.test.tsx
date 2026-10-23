import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/lib/api/client"
import type { ReportRead } from "@/lib/api/reports"
import enMessages from "@/messages/en.json"

import ReportDetailPage from "./page"

const mocks = vi.hoisted(() => ({
  refetch: vi.fn(),
  report: {
    isLoading: false,
    isError: false,
    error: null as unknown,
    data: undefined as ReportRead | undefined,
  },
}))

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "r1" }),
}))

vi.mock("@/lib/hooks/use-reports", () => ({
  useReport: () => ({ ...mocks.report, refetch: mocks.refetch }),
}))

function makeReport(
  hasActivity = true,
  kind: "monthly" | "weekly" = "monthly",
): ReportRead {
  const weekly = kind === "weekly"
  return {
    id: "r1",
    kind,
    period: weekly ? "2026-W42" : "2026-09",
    generated_at: weekly ? "2026-10-19T00:05:00Z" : "2026-10-01T00:05:00Z",
    payload: {
      version: 1,
      kind,
      period: weekly ? "2026-W42" : "2026-09",
      timezone: "Asia/Taipei",
      period_start: weekly ? "2026-10-12" : "2026-09-01",
      period_end: weekly ? "2026-10-18" : "2026-09-30",
      generated_at: weekly ? "2026-10-19T00:05:00Z" : "2026-10-01T00:05:00Z",
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
      valuation: { start: "100.00", end: "200.00", delta: "100.00", unpriced_items: 0 },
      top_categories: [],
      top_locations: [],
      has_activity: hasActivity,
    },
  }
}

function renderPage() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ReportDetailPage />
    </NextIntlClientProvider>,
  )
}

describe("ReportDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.report = {
      isLoading: false,
      isError: false,
      error: null,
      data: makeReport(),
    }
  })

  it("renders the skeleton while loading", () => {
    mocks.report = {
      isLoading: true,
      isError: false,
      error: null,
      data: undefined,
    }

    renderPage()

    expect(screen.getByLabelText(enMessages.reports.loading)).toBeInTheDocument()
  })

  it("renders the heading and summary on success", () => {
    renderPage()

    expect(
      screen.getByRole("heading", { name: "September 2026 report" }),
    ).toBeInTheDocument()
    expect(screen.getByTestId("report-inventory")).toBeInTheDocument()
    expect(screen.getByTestId("report-valuation")).toHaveTextContent("+NT$100")
  })

  it("links the breadcrumb back to the list", () => {
    renderPage()

    expect(
      screen.getByRole("link", { name: enMessages.reports.title }),
    ).toHaveAttribute("href", "/reports")
  })

  it("renders weekly heading, breadcrumb range and copy", () => {
    mocks.report.data = makeReport(true, "weekly")

    renderPage()

    expect(
      screen.getByRole("heading", {
        name: "Weekly report: Oct 12–18, 2026",
      }),
    ).toBeInTheDocument()
    expect(screen.getByText("Oct 12–18, 2026")).toBeInTheDocument()
    expect(screen.getByTestId("report-activity")).toHaveTextContent("This week")
    expect(screen.getByTestId("report-expiry")).toHaveTextContent(
      "Expiry at week end",
    )
  })

  it("shows a not-found message with a back link on 404", () => {
    mocks.report = {
      isLoading: false,
      isError: true,
      error: new ApiError(404, { detail: "report not found" }),
      data: undefined,
    }

    renderPage()

    expect(screen.getByText(enMessages.reports.detail.notFound)).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: enMessages.reports.detail.back }),
    ).toHaveAttribute("href", "/reports")
  })

  it("offers retry and back on a generic error", async () => {
    const user = userEvent.setup()
    mocks.report = {
      isLoading: false,
      isError: true,
      error: new ApiError(500, null),
      data: undefined,
    }

    renderPage()

    expect(screen.getByText(enMessages.reports.detail.loadError)).toBeInTheDocument()
    await user.click(
      screen.getByRole("button", { name: enMessages.reports.detail.retry }),
    )
    expect(mocks.refetch).toHaveBeenCalledTimes(1)
    expect(
      screen.getByRole("link", { name: enMessages.reports.detail.back }),
    ).toHaveAttribute("href", "/reports")
  })

  it("badges a month without activity", () => {
    mocks.report = {
      isLoading: false,
      isError: false,
      error: null,
      data: makeReport(false),
    }

    renderPage()

    expect(screen.getByText(enMessages.reports.noActivity)).toBeInTheDocument()
  })

  it("badges a week without activity with weekly copy", () => {
    mocks.report = {
      isLoading: false,
      isError: false,
      error: null,
      data: makeReport(false, "weekly"),
    }

    renderPage()

    expect(
      screen.getByText(enMessages.reports.noActivityWeekly),
    ).toBeInTheDocument()
  })
})
