import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { JobStatus } from "@/lib/api/jobs"
import enMessages from "@/messages/en.json"

import { RemindersPanel } from "./reminders-panel"

const mocks = vi.hoisted(() => ({
  useJobStatus: vi.fn(),
}))

vi.mock("@/lib/hooks/use-job-status", () => ({
  useJobStatus: mocks.useJobStatus,
}))

const t = enMessages.settings.reminders

function setStatus(overrides: Record<string, unknown> = {}) {
  mocks.useJobStatus.mockReturnValue({
    isLoading: false,
    isError: false,
    data: undefined,
    refetch: vi.fn(),
    ...overrides,
  })
}

const thresholds = {
  stale_after_hours: 26,
  advance_days: [30, 7, 0],
  expired_stop_days: 14,
}

const freshRun: JobStatus["last_run"] = {
  status: "succeeded",
  started_at: "2026-10-16T01:00:03Z",
  finished_at: "2026-10-16T01:00:05Z",
  result: { processed: 3, emitted: 2, errors: [] },
}

function renderPanel() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <RemindersPanel />
    </NextIntlClientProvider>,
  )
}

describe("RemindersPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setStatus()
  })

  it("shows a busy skeleton while loading", () => {
    setStatus({ isLoading: true })

    renderPanel()

    expect(screen.getByLabelText(t.loading)).toBeInTheDocument()
  })

  it("shows a retryable error state", () => {
    const refetch = vi.fn()
    setStatus({ isError: true, refetch })

    renderPanel()

    expect(screen.getByText(t.loadFailed)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: t.retry }))
    expect(refetch).toHaveBeenCalledTimes(1)
  })

  it("renders thresholds and warns when the job never ran", () => {
    setStatus({
      data: { job: "expiry-scan", thresholds, last_run: null, stale: true },
    })

    renderPanel()

    expect(screen.getByText(t.thresholdAdvance.replace("{days}", "30"))).toBeInTheDocument()
    expect(screen.getByText(t.thresholdAdvance.replace("{days}", "7"))).toBeInTheDocument()
    expect(screen.getByText(t.thresholdDueToday)).toBeInTheDocument()
    expect(
      screen.getByText(t.thresholdExpiredStop.replace("{days}", "14")),
    ).toBeInTheDocument()
    expect(screen.getByText(t.lastRunNever)).toBeInTheDocument()
    expect(screen.getByText(t.warnNever)).toBeInTheDocument()
    expect(screen.getByText(/expiry-scan\/run/)).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: t.setupPatLink }),
    ).toHaveAttribute("href", "/settings/tokens")
    expect(
      screen.getByRole("link", { name: t.setupDocsLink }),
    ).toHaveAttribute(
      "href",
      "https://github.com/guan4tou2/Item-Manage-System/blob/main/docs/scheduling.md",
    )
  })

  it("renders the last run and the stale warning when overdue", () => {
    setStatus({
      data: {
        job: "expiry-scan",
        thresholds,
        last_run: {
          ...freshRun,
          started_at: "2026-10-14T01:00:03Z",
          finished_at: "2026-10-14T01:00:05Z",
        },
        stale: true,
      },
    })

    renderPanel()

    expect(screen.getByText(t.warnStale.replace("{hours}", "26"))).toBeInTheDocument()
    expect(screen.getByText(t.lastRunSucceeded)).toBeInTheDocument()
    expect(
      screen.getByText(t.lastRunSummary.replace("{processed}", "3").replace("{emitted}", "2")),
    ).toBeInTheDocument()
  })

  it("shows a healthy last run without warnings", () => {
    setStatus({
      data: { job: "expiry-scan", thresholds, last_run: freshRun, stale: false },
    })

    renderPanel()

    expect(screen.getByText(t.lastRunSucceeded)).toBeInTheDocument()
    expect(screen.queryByText(t.warnNever)).not.toBeInTheDocument()
    expect(screen.queryByText(/No run for over/)).not.toBeInTheDocument()
  })

  it("surfaces a failed last run", () => {
    setStatus({
      data: {
        job: "expiry-scan",
        thresholds,
        last_run: { ...freshRun, status: "failed" },
        stale: false,
      },
    })

    renderPanel()

    expect(screen.getByText(t.lastRunFailed)).toBeInTheDocument()
    expect(screen.getByText(t.warnFailed)).toBeInTheDocument()
  })
})
