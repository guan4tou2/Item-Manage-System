import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"

import { ReportsEmpty } from "./reports-empty"

function renderEmpty(disabled?: boolean, locale = "en") {
  return render(
    <NextIntlClientProvider
      locale={locale}
      messages={locale === "zh-TW" ? zhMessages : enMessages}
    >
      <ReportsEmpty disabled={disabled} />
    </NextIntlClientProvider>,
  )
}

describe("ReportsEmpty", () => {
  it("explains the first report for a fresh account", () => {
    renderEmpty()

    expect(screen.getByText(enMessages.reports.empty.title)).toBeInTheDocument()
    expect(screen.getByText(enMessages.reports.empty.firstMonth)).toBeInTheDocument()
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
  })

  it("links to the settings page when monthly reports are disabled", () => {
    renderEmpty(true)

    expect(screen.getByText(enMessages.reports.empty.disabled)).toBeInTheDocument()
    expect(screen.getByText(enMessages.reports.empty.disabledHint)).toBeInTheDocument()
    expect(screen.getByRole("link")).toHaveAttribute("href", "/settings/reports")
  })

  it("renders zh-TW copy", () => {
    renderEmpty(false, "zh-TW")

    expect(screen.getByText("還沒有月報")).toBeInTheDocument()
  })
})
