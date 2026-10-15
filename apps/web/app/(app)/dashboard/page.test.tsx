import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import DashboardPage from "./page"

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/hooks/use-stats", () => ({
  useOverview: () => ({ data: undefined, isLoading: false }),
  useRecent: () => ({ data: [], isLoading: false }),
  useLowStock: () => ({ data: [], isLoading: false }),
  useActiveLoans: () => ({ data: [], isLoading: false }),
  useActivity: () => ({ data: [], isLoading: false }),
  useExpiryStats: () => ({
    data: {
      expired_count: 2,
      expiring_count: 1,
      items: [],
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}))

describe("DashboardPage action cards", () => {
  it("presents the expiry card before the low stock card", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <DashboardPage />
      </NextIntlClientProvider>,
    )

    const expiry = screen.getByTestId("expiry-card")
    const lowStock = screen.getByText("Low stock alert")
    expect(
      expiry.compareDocumentPosition(lowStock) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })
})
