import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { MonthlyReportPanel } from "./monthly-report-panel"

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  refetch: vi.fn(),
  prefs: {
    isLoading: false,
    isError: false,
    data: { report_monthly_enabled: true } as
      | { report_monthly_enabled: boolean }
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
      <MonthlyReportPanel />
    </NextIntlClientProvider>,
  )
}

describe("MonthlyReportPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.prefs = {
      isLoading: false,
      isError: false,
      data: { report_monthly_enabled: true },
    }
    mocks.mutateAsync.mockResolvedValue({ report_monthly_enabled: false })
  })

  it("shows the skeleton while loading", () => {
    mocks.prefs = { isLoading: true, isError: false, data: undefined }

    renderPanel()

    expect(screen.getByLabelText(t.loading)).toBeInTheDocument()
  })

  it("renders the toggle as checked by default", () => {
    renderPanel()

    expect(screen.getByRole("switch", { name: t.toggleTitle })).toBeChecked()
    expect(screen.getByTestId("report-schedule-note")).toHaveTextContent(t.scheduleNote)
    expect(screen.getByRole("link", { name: t.historyLink })).toHaveAttribute(
      "href",
      "/reports",
    )
  })

  it("sends the off payload and toasts on success", async () => {
    renderPanel()

    fireEvent.click(screen.getByRole("switch", { name: t.toggleTitle }))

    expect(mocks.mutateAsync).toHaveBeenCalledWith({
      report_monthly_enabled: false,
    })
    await vi.waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(t.savedOff)
    })
  })

  it("sends the on payload when enabling again", async () => {
    mocks.prefs = {
      isLoading: false,
      isError: false,
      data: { report_monthly_enabled: false },
    }

    renderPanel()

    expect(screen.getByRole("switch", { name: t.toggleTitle })).not.toBeChecked()
    fireEvent.click(screen.getByRole("switch", { name: t.toggleTitle }))

    expect(mocks.mutateAsync).toHaveBeenCalledWith({
      report_monthly_enabled: true,
    })
    await vi.waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(t.savedOn)
    })
  })

  it("keeps the previous value and toasts on failure", async () => {
    mocks.mutateAsync.mockRejectedValue(new Error("boom"))

    renderPanel()

    fireEvent.click(screen.getByRole("switch", { name: t.toggleTitle }))

    await vi.waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(t.saveFailed)
    })
    expect(toast.success).not.toHaveBeenCalled()
    expect(screen.getByRole("switch", { name: t.toggleTitle })).toBeChecked()
  })

  it("retries after a load error", () => {
    mocks.prefs = { isLoading: false, isError: true, data: undefined }

    renderPanel()

    expect(screen.getByText(t.loadError)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: t.retry }))
    expect(mocks.refetch).toHaveBeenCalledTimes(1)
  })
})
