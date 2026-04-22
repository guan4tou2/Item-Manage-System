import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"
import { RecentItemsCard } from "./recent-items-card"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

describe("RecentItemsCard", () => {
  it("renders empty state when items is empty", () => {
    render(<RecentItemsCard items={[]} />, { wrapper: Provider })
    expect(screen.getByText("No items yet")).toBeInTheDocument()
  })

  it("lists item names when items provided", () => {
    render(
      <RecentItemsCard
        items={[
          { id: "a", name: "Apple" } as never,
          { id: "b", name: "Banana" } as never,
        ]}
      />,
      { wrapper: Provider },
    )
    expect(screen.getByText("Apple")).toBeInTheDocument()
    expect(screen.getByText("Banana")).toBeInTheDocument()
  })
})
