import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import type { ValueStats } from "@/lib/api/stats"
import enMessages from "@/messages/en.json"

import { ValueCard } from "./value-card"

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

function renderCard(
  props: {
    stats?: ValueStats
    loading?: boolean
    error?: boolean
    onRetry?: () => void
  } = {},
) {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ValueCard {...props} />
    </NextIntlClientProvider>,
  )
}

describe("ValueCard", () => {
  it("renders the formatted amount, unpriced note, and statistics link", () => {
    renderCard({ stats: base })

    expect(screen.getByTestId("value-card-amount")).toHaveTextContent("NT$1,200")
    expect(screen.getByText("No cost yet for 1 of 2 items")).toBeInTheDocument()
    const link = screen.getByTestId("value-card-link")
    expect(link).toHaveTextContent(enMessages.dashboard.value.viewStats)
    expect(link).toHaveAttribute("href", "/statistics")
  })

  it("guides to fill costs when nothing has been priced", () => {
    renderCard({ stats: { ...base, total_value: "0.00", priced_items: 0, unpriced_items: 2 } })

    expect(screen.getByTestId("value-card-amount")).toHaveTextContent("NT$0")
    expect(screen.getByText(enMessages.dashboard.value.emptyNote)).toBeInTheDocument()
    expect(screen.getByTestId("value-card-link")).toHaveAttribute("href", "/items")
  })

  it("shows a skeleton while loading", () => {
    renderCard({ loading: true })

    expect(screen.getByTestId("value-card-skeleton")).toBeInTheDocument()
    expect(screen.queryByTestId("value-card-amount")).not.toBeInTheDocument()
  })

  it("shows a compact error with a retry", async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    renderCard({ error: true, onRetry })

    expect(screen.getByRole("alert")).toHaveTextContent(enMessages.dashboard.value.loadFailed)
    await user.click(screen.getByRole("button", { name: enMessages.dashboard.value.retry }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
