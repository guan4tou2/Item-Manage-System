import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import SettingsReportsPage from "./page"

vi.mock("@/components/settings/monthly-report-panel", () => ({
  MonthlyReportPanel: () => <div data-testid="monthly-report-panel" />,
}))

describe("SettingsReportsPage", () => {
  it("renders the shell title and mounts the monthly report panel", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <SettingsReportsPage />
      </NextIntlClientProvider>,
    )

    expect(
      screen.getByRole("heading", {
        name: enMessages.settings.index.pages.reports.title,
      }),
    ).toBeInTheDocument()
    expect(screen.getByTestId("monthly-report-panel")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: enMessages.settings.title })).toHaveAttribute(
      "href",
      "/settings",
    )
  })
})
