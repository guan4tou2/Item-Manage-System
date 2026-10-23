import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { ReportsPanel } from "./reports-panel"

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  refetch: vi.fn(),
  prefs: {
    isLoading: false,
    isError: false,
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

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: () => ({ ...mocks.prefs, refetch: mocks.refetch }),
  useUpdatePreferences: () => ({
    isPending: false,
    mutateAsync: mocks.mutateAsync,
  }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from "sonner"

const t = enMessages.settings.reports

function renderPanel() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ReportsPanel />
    </NextIntlClientProvider>,
  )
}

describe("ReportsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.prefs = {
      isLoading: false,
      isError: false,
      data: {
        report_monthly_enabled: true,
        report_weekly_enabled: false,
      },
    }
    mocks.mutateAsync.mockResolvedValue({
      report_monthly_enabled: false,
      report_weekly_enabled: true,
    })
  })

  it("shows the skeleton while loading", () => {
    mocks.prefs = { isLoading: true, isError: false, data: undefined }

    renderPanel()

    expect(screen.getByLabelText(t.loading)).toBeInTheDocument()
  })

  it("renders monthly on and weekly off by default", () => {
    renderPanel()

    expect(screen.getByRole("switch", { name: t.toggleTitle })).toBeChecked()
    expect(screen.getByRole("switch", { name: t.weeklyTitle })).not.toBeChecked()
    expect(screen.getByTestId("report-schedule-note")).toHaveTextContent(
      t.scheduleNote,
    )
    expect(screen.getByTestId("weekly-report-schedule-note")).toHaveTextContent(
      t.weeklyScheduleNote,
    )
    expect(screen.getByRole("link", { name: t.historyLink })).toHaveAttribute(
      "href",
      "/reports",
    )
  })

  it("sends only the monthly key and toasts on success", async () => {
    renderPanel()

    fireEvent.click(screen.getByRole("switch", { name: t.toggleTitle }))

    expect(mocks.mutateAsync).toHaveBeenCalledWith({
      report_monthly_enabled: false,
    })
    await vi.waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(t.monthlySavedOff)
    })
  })

  it("sends only the weekly key and toasts on success", async () => {
    renderPanel()

    fireEvent.click(screen.getByRole("switch", { name: t.weeklyTitle }))

    expect(mocks.mutateAsync).toHaveBeenCalledWith({
      report_weekly_enabled: true,
    })
    await vi.waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(t.weeklySavedOn)
    })
  })

  it("toggles weekly off independently from monthly", async () => {
    mocks.prefs = {
      isLoading: false,
      isError: false,
      data: {
        report_monthly_enabled: true,
        report_weekly_enabled: true,
      },
    }

    renderPanel()

    expect(screen.getByRole("switch", { name: t.weeklyTitle })).toBeChecked()
    fireEvent.click(screen.getByRole("switch", { name: t.weeklyTitle }))

    expect(mocks.mutateAsync).toHaveBeenCalledWith({
      report_weekly_enabled: false,
    })
    await vi.waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(t.weeklySavedOff)
    })
    expect(screen.getByRole("switch", { name: t.toggleTitle })).toBeChecked()
  })

  it("keeps the previous value and toasts on failure", async () => {
    mocks.mutateAsync.mockRejectedValue(new Error("boom"))

    renderPanel()

    fireEvent.click(screen.getByRole("switch", { name: t.weeklyTitle }))

    await vi.waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(t.saveFailed)
    })
    expect(toast.success).not.toHaveBeenCalled()
    expect(screen.getByRole("switch", { name: t.weeklyTitle })).not.toBeChecked()
  })

  it("retries after a load error", () => {
    mocks.prefs = { isLoading: false, isError: true, data: undefined }

    renderPanel()

    expect(screen.getByText(t.loadError)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: t.retry }))
    expect(mocks.refetch).toHaveBeenCalledTimes(1)
  })
})
