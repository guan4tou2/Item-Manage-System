import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import type { ValueStats } from "@/lib/api/stats"
import enMessages from "@/messages/en.json"

import { ValueSummaryCard } from "./value-summary-card"

const base: ValueStats = {
  currency: "TWD",
  total_value: "1200.00",
  priced_items: 1,
  unpriced_items: 1,
  total_items: 2,
  by_category: [],
  by_location: [],
  by_warehouse: [],
}

function renderCard(data?: ValueStats, loading = false) {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ValueSummaryCard data={data} loading={loading} />
    </NextIntlClientProvider>,
  )
}

describe("ValueSummaryCard", () => {
  it("renders the formatted total with the priced/unpriced ratio", () => {
    renderCard(base)

    expect(screen.getByTestId("value-summary")).toHaveTextContent("NT$1,200")
    expect(screen.getByText(/Priced 1\/2 items/)).toBeInTheDocument()
    expect(screen.getByText(/Unpriced 1 \(50%\)/)).toBeInTheDocument()
    expect(screen.getByText(/counted as NT\$0/)).toBeInTheDocument()
  })

  it("shows guidance when no cost has been recorded", () => {
    renderCard({ ...base, total_value: "0.00", priced_items: 0, unpriced_items: 2 })

    expect(screen.getByTestId("value-summary")).toHaveTextContent("NT$0")
    expect(screen.getByText(enMessages.stats.value.zeroTotal)).toBeInTheDocument()
  })

  it("shows a skeleton while loading", () => {
    renderCard(undefined, true)

    expect(screen.getByTestId("value-summary-skeleton")).toBeInTheDocument()
    expect(screen.queryByTestId("value-summary")).not.toBeInTheDocument()
  })
})
