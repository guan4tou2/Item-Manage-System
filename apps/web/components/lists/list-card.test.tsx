import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"
import { ListCard } from "./list-card"
import type { ListSummary } from "@/lib/api/lists"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const baseRow: ListSummary = {
  id: "id1",
  kind: "travel",
  title: "Japan 10 Days",
  description: null,
  start_date: "2026-05-01",
  end_date: "2026-05-10",
  budget: null,
  entry_count: 12,
  done_count: 3,
  created_at: "2026-04-23T00:00:00Z",
  updated_at: "2026-04-23T00:00:00Z",
}

describe("ListCard", () => {
  it("renders title", () => {
    render(<ListCard row={baseRow} />, { wrapper: Provider })
    expect(screen.getByText("Japan 10 Days")).toBeInTheDocument()
  })

  it("renders entry count", () => {
    render(<ListCard row={baseRow} />, { wrapper: Provider })
    expect(screen.getByText(/12 items · 3 done/i)).toBeInTheDocument()
  })

  it("renders date range for travel", () => {
    render(<ListCard row={baseRow} />, { wrapper: Provider })
    expect(screen.getByText(/2026-05-01 – 2026-05-10/)).toBeInTheDocument()
  })

  it("renders budget for shopping", () => {
    const shop: ListSummary = { ...baseRow, kind: "shopping", start_date: null, end_date: null, budget: "2000.00" }
    render(<ListCard row={shop} />, { wrapper: Provider })
    expect(screen.getByText(/Budget \$2000\.00/)).toBeInTheDocument()
  })
})
