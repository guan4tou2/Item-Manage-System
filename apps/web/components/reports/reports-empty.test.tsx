import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"

import { ReportsEmpty } from "./reports-empty"

function renderEmpty(
  props: { monthlyEnabled?: boolean; weeklyEnabled?: boolean } = {},
  locale = "en",
) {
  return render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "zh-TW" ? zhMessages : enMessages}
    >
      <ReportsEmpty {...props} />
    </NextIntlClientProvider>,
  )
}

describe("ReportsEmpty", () => {
  it("explains the first monthly report for a fresh account", () => {
    renderEmpty()

    expect(screen.getByText(enMessages.reports.empty.title)).toBeInTheDocument()
    expect(screen.getByText(enMessages.reports.empty.firstMonth)).toBeInTheDocument()
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
  })

  it("keeps the monthly first-report copy when weekly is also enabled", () => {
    renderEmpty({ monthlyEnabled: true, weeklyEnabled: true })

    expect(screen.getByText(enMessages.reports.empty.firstMonth)).toBeInTheDocument()
  })

  it("links to settings when both report kinds are disabled", () => {
    renderEmpty({ monthlyEnabled: false, weeklyEnabled: false })

    expect(screen.getByText(enMessages.reports.empty.disabled)).toBeInTheDocument()
    expect(screen.getByText(enMessages.reports.empty.disabledHint)).toBeInTheDocument()
    expect(screen.getByRole("link")).toHaveAttribute("href", "/settings/reports")
  })

  it("explains the first weekly report when only weekly is enabled", () => {
    renderEmpty({ monthlyEnabled: false, weeklyEnabled: true })

    expect(screen.getByText(enMessages.reports.empty.weeklyOnly)).toBeInTheDocument()
    expect(
      screen.getByText(enMessages.reports.empty.weeklyOnlyHint),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: enMessages.reports.empty.openSettings }),
    ).toHaveAttribute("href", "/settings/reports")
  })

  it("renders zh-TW copy", () => {
    renderEmpty({}, "zh-TW")

    expect(screen.getByText("還沒有報表")).toBeInTheDocument()
  })
})
