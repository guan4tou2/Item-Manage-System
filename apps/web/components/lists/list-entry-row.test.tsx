import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { ListEntryRow } from "./list-entry-row"
import type { ListEntry } from "@/lib/api/lists"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const baseEntry: ListEntry = {
  id: "e1",
  list_id: "l1",
  position: 0,
  name: "Passport",
  quantity: 2,
  note: "In the drawer",
  price: null,
  link: null,
  is_done: false,
  created_at: "2026-04-23T00:00:00Z",
  updated_at: "2026-04-23T00:00:00Z",
}

describe("ListEntryRow", () => {
  it("renders name and note", () => {
    render(
      <ListEntryRow entry={baseEntry} onToggle={vi.fn()} onDelete={vi.fn()} />,
      { wrapper: Provider },
    )
    expect(screen.getByText("Passport")).toBeInTheDocument()
    expect(screen.getByText(/In the drawer/)).toBeInTheDocument()
  })

  it("fires onToggle when checkbox clicked", () => {
    const onToggle = vi.fn()
    render(
      <ListEntryRow entry={baseEntry} onToggle={onToggle} onDelete={vi.fn()} />,
      { wrapper: Provider },
    )
    fireEvent.click(screen.getByRole("checkbox"))
    expect(onToggle).toHaveBeenCalledWith("e1")
  })

  it("fires onDelete when delete button clicked", () => {
    const onDelete = vi.fn()
    render(
      <ListEntryRow entry={baseEntry} onToggle={vi.fn()} onDelete={onDelete} />,
      { wrapper: Provider },
    )
    fireEvent.click(screen.getByRole("button", { name: /delete/i }))
    expect(onDelete).toHaveBeenCalledWith("e1")
  })

  it("renders price when present", () => {
    render(
      <ListEntryRow
        entry={{ ...baseEntry, price: "99.50" }}
        onToggle={vi.fn()}
        onDelete={vi.fn()}
      />,
      { wrapper: Provider },
    )
    expect(screen.getByText(/\$99\.50/)).toBeInTheDocument()
  })

  it("applies opacity when done", () => {
    const { container } = render(
      <ListEntryRow
        entry={{ ...baseEntry, is_done: true }}
        onToggle={vi.fn()}
        onDelete={vi.fn()}
      />,
      { wrapper: Provider },
    )
    expect(container.firstChild).toHaveClass("opacity-60")
  })
})
