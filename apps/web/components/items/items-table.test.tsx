import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import type { ItemRead } from "@/lib/api/items"
import enMessages from "@/messages/en.json"
import { taipeiTodayIso } from "./expiry-badge"
import { ItemsTable } from "./items-table"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/batches", () => ({
  listBatches: vi.fn(),
}))

import * as batchApi from "@/lib/api/batches"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const BatchProvider = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        {children}
      </NextIntlClientProvider>
    </QueryClientProvider>
  )
}

function iso(offsetDays: number): string {
  const base = Date.parse(`${taipeiTodayIso()}T00:00:00Z`)
  return new Date(base + offsetDays * 86_400_000).toISOString().slice(0, 10)
}

const items: ItemRead[] = [
  {
    id: "item-1",
    name: "Router",
    description: null,
    quantity: 1,
    min_quantity: null,
    track_batches: false,
    notes: null,
    is_favorite: false,
    image_id: null,
    warehouse_id: null,
    owner_id: "owner-1",
    owner_username: "owner",
    created_at: "2026-06-23T00:00:00Z",
    updated_at: "2026-06-23T00:00:00Z",
    category: null,
    location: {
      id: 2,
      parent_id: 1,
      name: "Kitchen",
      kind: "room",
      sort_order: 0,
      floor_plan_image_id: null,
      path: "1F / Kitchen",
    },
    tags: [{ id: 1, name: "network" }],
  },
  {
    id: "item-2",
    name: "Switch",
    description: null,
    quantity: 2,
    min_quantity: null,
    track_batches: false,
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

  it("shows a single soonest-expiry badge on tracked rows only", () => {
    render(
      <ItemsTable
        items={[
          { ...items[0]!, id: "item-3", name: "Milk", track_batches: true, soonest_expiry: iso(-3) },
          { ...items[1]!, id: "item-4", name: "Coffee", track_batches: true, soonest_expiry: iso(30) },
        ]}
      />,
      { wrapper: Provider },
    )

    const badges = screen.getAllByText("Expired 3d")
    expect(badges).toHaveLength(1)
    expect(badges[0]).toHaveAttribute("data-status", "expired")
    expect(screen.queryByText(iso(30))).not.toBeInTheDocument()
  })

  it("leaves untracked rows unchanged even with a stale expiry", () => {
    render(<ItemsTable items={[{ ...items[0]!, track_batches: false, soonest_expiry: iso(-1) }]} />, {
      wrapper: Provider,
    })

    expect(screen.queryByText("Expired 1d")).not.toBeInTheDocument()
  })

  it("exposes −1 and batch expansion in expiry mode", async () => {
    const onConsumeOne = vi.fn()
    vi.mocked(batchApi.listBatches).mockResolvedValue([
      {
        id: "batch-1",
        quantity: 2,
        expiry_date: iso(5),
        note: null,
        is_depleted: false,
      } as never,
    ])

    render(
      <ItemsTable
        items={[
          { ...items[0]!, track_batches: true, soonest_expiry: iso(2), quantity: 4 },
          { ...items[1]!, id: "item-5", name: "Empty", track_batches: true, quantity: 0, soonest_expiry: null },
        ]}
        expiryMode
        onConsumeOne={onConsumeOne}
      />,
      { wrapper: BatchProvider },
    )

    fireEvent.click(screen.getByRole("button", { name: "Consume 1: Router" }))
    expect(onConsumeOne).toHaveBeenCalledWith(expect.objectContaining({ id: "item-1" }))
    expect(screen.getByRole("button", { name: "Consume 1: Empty" })).toBeDisabled()
    expect(screen.getByText("2d left")).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole("button", { name: "Expand batches" })[0]!)

    expect(await screen.findByText("5d left")).toBeInTheDocument()
    expect(screen.getByText("2 left")).toBeInTheDocument()
  })

  it("renders the location path (middle-truncated with a full title)", () => {
    const deep = [
      {
        ...items[0]!,
        location: { ...items[0]!.location!, path: "1F / 廚房 / 上櫃 / 抽屜" },
      },
    ]
    render(<ItemsTable items={deep} />, { wrapper: Provider })

    const cell = screen.getAllByTestId("items-table-location-cell")[0]!
    expect(cell).toHaveTextContent("1F / … / 抽屜")
    expect(cell.querySelector("span")).toHaveAttribute("title", "1F / 廚房 / 上櫃 / 抽屜")
  })

})
