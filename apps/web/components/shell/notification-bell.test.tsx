import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { NotificationBell } from "./notification-bell"

const mockState: { value: { data?: { count: number }; isLoading: boolean } } = {
  value: { data: { count: 0 }, isLoading: false },
}

vi.mock("@/lib/hooks/use-notifications", () => ({
  useUnreadCount: () => mockState.value,
}))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

describe("NotificationBell", () => {
  it("hides badge when count is 0", () => {
    mockState.value = { data: { count: 0 }, isLoading: false }
    render(<NotificationBell />, { wrapper: Provider })
    expect(screen.queryByTestId("notification-badge")).not.toBeInTheDocument()
  })

  it("shows count when 1..99", () => {
    mockState.value = { data: { count: 7 }, isLoading: false }
    render(<NotificationBell />, { wrapper: Provider })
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("7")
  })

  it("shows 99+ when count exceeds 99", () => {
    mockState.value = { data: { count: 150 }, isLoading: false }
    render(<NotificationBell />, { wrapper: Provider })
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("99+")
  })
})
