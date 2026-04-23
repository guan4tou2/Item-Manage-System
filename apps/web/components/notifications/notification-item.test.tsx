import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { NotificationItem } from "./notification-item"
import type { NotificationRead } from "@/lib/api/notifications"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const baseRow: NotificationRead = {
  id: "id-1",
  user_id: "u1",
  type: "system.welcome",
  title: "Welcome",
  body: "Start from the dashboard.",
  link: "/dashboard",
  read_at: null,
  created_at: new Date().toISOString(),
}

describe("NotificationItem", () => {
  it("renders title and body", () => {
    render(<NotificationItem row={baseRow} onOpen={vi.fn()} onDelete={vi.fn()} />, { wrapper: Provider })
    expect(screen.getByText("Welcome")).toBeInTheDocument()
    expect(screen.getByText("Start from the dashboard.")).toBeInTheDocument()
  })

  it("shows unread dot when read_at is null", () => {
    render(<NotificationItem row={baseRow} onOpen={vi.fn()} onDelete={vi.fn()} />, { wrapper: Provider })
    expect(screen.getByTestId("unread-dot")).toBeInTheDocument()
  })

  it("hides unread dot when row is read", () => {
    render(
      <NotificationItem
        row={{ ...baseRow, read_at: new Date().toISOString() }}
        onOpen={vi.fn()}
        onDelete={vi.fn()}
      />,
      { wrapper: Provider },
    )
    expect(screen.queryByTestId("unread-dot")).not.toBeInTheDocument()
  })

  it("fires onOpen when row is clicked", () => {
    const onOpen = vi.fn()
    render(<NotificationItem row={baseRow} onOpen={onOpen} onDelete={vi.fn()} />, { wrapper: Provider })
    fireEvent.click(screen.getByRole("button", { name: /open notification/i }))
    expect(onOpen).toHaveBeenCalledWith(baseRow)
  })

  it("fires onDelete when delete button clicked", () => {
    const onDelete = vi.fn()
    render(<NotificationItem row={baseRow} onOpen={vi.fn()} onDelete={onDelete} />, { wrapper: Provider })
    fireEvent.click(screen.getByRole("button", { name: /delete/i }))
    expect(onDelete).toHaveBeenCalledWith(baseRow.id)
  })
})
