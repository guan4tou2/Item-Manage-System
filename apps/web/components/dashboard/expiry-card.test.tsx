import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import type { ExpiryStats } from "@/lib/api/stats"
import enMessages from "@/messages/en.json"

import { ExpiryCard } from "./expiry-card"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const stats: ExpiryStats = {
  expired_count: 2,
  expiring_count: 1,
  items: [
    {
      item_id: "item-1",
      name: "Milk",
      quantity: 3,
      soonest_expiry: "2026-10-10",
      days_left: -6,
      status: "expired",
    },
  ],
}

describe("ExpiryCard", () => {
  it("maps the counts to their filtered deep links", () => {
    render(<ExpiryCard stats={stats} />, { wrapper: Provider })

    expect(screen.getByText("2 items")).toBeInTheDocument()
    expect(screen.getByText("1 item")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Expired/ })).toHaveAttribute(
      "href",
      "/items?expiry=expired&sort=expiry_asc",
    )
    expect(screen.getByRole("link", { name: /Expiring within 7 days/ })).toHaveAttribute(
      "href",
      "/items?expiry=expiring_soon&sort=expiry_asc",
    )
  })

  it("annotates the soonest item as the status note", () => {
    render(<ExpiryCard stats={stats} />, { wrapper: Provider })

    expect(screen.getByTestId("expiry-card-note")).toHaveTextContent(
      "Soonest: Milk, expired 6d ago",
    )
  })

  it("shows the quiet empty state when nothing is expiring", () => {
    render(<ExpiryCard stats={{ expired_count: 0, expiring_count: 0, items: [] }} />, {
      wrapper: Provider,
    })

    expect(screen.getByText("All clear · nothing expiring")).toBeInTheDocument()
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
  })

  it("renders skeletons while loading", () => {
    render(<ExpiryCard loading />, { wrapper: Provider })

    expect(screen.getAllByTestId("expiry-card-skeleton")).toHaveLength(2)
  })

  it("keeps failures compact with a retry action", () => {
    const onRetry = vi.fn()
    render(<ExpiryCard error onRetry={onRetry} />, { wrapper: Provider })

    expect(screen.getByText("Could not load expiry data.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    expect(onRetry).toHaveBeenCalled()
  })
})
