import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ValueStats } from "@/lib/api/stats"
import enMessages from "@/messages/en.json"

import { ValueSection } from "./value-section"

interface ValueQuery {
  data?: ValueStats
  isLoading: boolean
  isError: boolean
  refetch: ReturnType<typeof vi.fn>
}

const mocks = vi.hoisted(() => ({
  value: {
    data: undefined,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as ValueQuery,
}))

vi.mock("@/lib/hooks/use-stats", () => ({
  useStatsValue: () => mocks.value,
}))

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

beforeEach(() => {
  mocks.value = {
    data: undefined,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }
})

function renderSection() {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ValueSection />
    </NextIntlClientProvider>,
  )
}

describe("ValueSection", () => {
  it("renders the heading, summary, and both value charts", () => {
    mocks.value.data = base
    renderSection()

    expect(
      screen.getByRole("heading", { level: 2, name: enMessages.stats.value.sectionTitle }),
    ).toBeInTheDocument()
    expect(screen.getByTestId("value-summary")).toHaveTextContent("NT$1,200")
    expect(screen.getByText(enMessages.stats.value.byCategory)).toBeInTheDocument()
    expect(screen.getByText(enMessages.stats.value.byLocation)).toBeInTheDocument()
  })

  it("renders empty states for both charts when there is no data yet", () => {
    mocks.value.data = {
      ...base,
      total_value: "0.00",
      priced_items: 0,
      unpriced_items: 0,
      total_items: 0,
    }
    renderSection()

    expect(screen.getAllByText(enMessages.stats.empty.title)).toHaveLength(2)
  })

  it("shows a compact error with a retry that refetches", async () => {
    const user = userEvent.setup()
    mocks.value.isError = true
    renderSection()

    expect(screen.getByRole("alert")).toHaveTextContent(enMessages.stats.value.error)
    expect(screen.queryByTestId("value-summary")).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: enMessages.stats.value.retry }))
    expect(mocks.value.refetch).toHaveBeenCalledTimes(1)
  })
})
