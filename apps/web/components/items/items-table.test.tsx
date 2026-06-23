import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import type { ItemRead } from "@/lib/api/items"
import enMessages from "@/messages/en.json"
import { ItemsTable } from "./items-table"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const items: ItemRead[] = [
  {
    id: "item-1",
    name: "Router",
    description: null,
    quantity: 1,
    min_quantity: null,
    notes: null,
    is_favorite: false,
    image_id: null,
    warehouse_id: null,
    owner_id: "owner-1",
    owner_username: "owner",
    created_at: "2026-06-23T00:00:00Z",
    updated_at: "2026-06-23T00:00:00Z",
    category: null,
    location: null,
    tags: [{ id: 1, name: "network" }],
  },
  {
    id: "item-2",
    name: "Switch",
    description: null,
    quantity: 2,
    min_quantity: null,
    notes: null,
    is_favorite: false,
    image_id: null,
    warehouse_id: null,
    owner_id: "owner-1",
    owner_username: "owner",
    created_at: "2026-06-23T00:00:00Z",
    updated_at: "2026-06-23T00:00:00Z",
    category: null,
    location: null,
    tags: [],
  },
]

describe("ItemsTable", () => {
  it("selects a single item", () => {
    const onSelectionChange = vi.fn()
    render(
      <ItemsTable items={items} selectedIds={[]} onSelectionChange={onSelectionChange} />,
      { wrapper: Provider },
    )

    fireEvent.click(screen.getByRole("checkbox", { name: "Select Router" }))

    expect(onSelectionChange).toHaveBeenCalledWith(["item-1"])
  })

  it("selects and clears all selectable rows", () => {
    const onSelectionChange = vi.fn()
    const { rerender } = render(
      <ItemsTable items={items} selectedIds={[]} onSelectionChange={onSelectionChange} />,
      { wrapper: Provider },
    )

    fireEvent.click(screen.getByRole("checkbox", { name: "Select all items" }))
    expect(onSelectionChange).toHaveBeenCalledWith(["item-1", "item-2"])

    rerender(
      <Provider>
        <ItemsTable
          items={items}
          selectedIds={["item-1", "item-2"]}
          onSelectionChange={onSelectionChange}
        />
      </Provider>,
    )
    fireEvent.click(screen.getByRole("checkbox", { name: "Select all items" }))
    expect(onSelectionChange).toHaveBeenLastCalledWith([])
  })

  it("does not select disabled rows from the header checkbox", () => {
    const onSelectionChange = vi.fn()
    render(
      <ItemsTable
        items={items}
        selectedIds={[]}
        onSelectionChange={onSelectionChange}
        getRowDisabled={(item) => item.id === "item-2"}
      />,
      { wrapper: Provider },
    )

    fireEvent.click(screen.getByRole("checkbox", { name: "Select all items" }))

    expect(screen.getByRole("checkbox", { name: "Select Switch" })).toBeDisabled()
    expect(onSelectionChange).toHaveBeenCalledWith(["item-1"])
  })

  it("adds field labels for compact mobile rows", () => {
    render(<ItemsTable items={items} />, { wrapper: Provider })

    expect(screen.getAllByTestId("items-table-name-cell")[0]).toHaveAttribute("data-label", "Name")
    expect(screen.getAllByTestId("items-table-category-cell")[0]).toHaveAttribute("data-label", "Category")
    expect(screen.getAllByTestId("items-table-location-cell")[0]).toHaveAttribute("data-label", "Location")
    expect(screen.getAllByTestId("items-table-quantity-cell")[0]).toHaveAttribute("data-label", "Qty")
    expect(screen.getAllByTestId("items-table-tags-cell")[0]).toHaveAttribute("data-label", "Tags")
  })
})
