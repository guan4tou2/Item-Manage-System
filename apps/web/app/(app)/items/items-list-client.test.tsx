import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { ItemRead } from "@/lib/api/items"
import * as itemsApi from "@/lib/api/items"
import enMessages from "@/messages/en.json"

import { ItemsListClient } from "./items-list-client"

const replace = vi.fn()

vi.mock("next/navigation", () => ({
  usePathname: () => "/items",
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/hooks/use-categories", () => ({
  useCategories: () => ({ data: [] }),
}))

vi.mock("@/lib/hooks/use-locations", () => ({
  useLocations: () => ({
    data: [
      { id: 7, floor: "1F", room: "Storage", zone: "A" },
      { id: 8, floor: "2F", room: "Lab", zone: null },
    ],
  }),
}))

vi.mock("@/lib/hooks/use-tags", () => ({
  useTags: () => ({ data: [{ id: 1, name: "network" }] }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

function item(id: string, name: string): ItemRead {
  return {
    id,
    name,
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
    tags: [],
  }
}

function renderClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ItemsListClient />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("ItemsListClient bulk actions", () => {
  beforeEach(() => {
    replace.mockReset()
    vi.restoreAllMocks()
    vi.spyOn(itemsApi, "listItems").mockResolvedValue({
      items: [item("item-1", "Router"), item("item-2", "Switch")],
      total: 2,
      page: 1,
      per_page: 20,
    })
    vi.spyOn(itemsApi, "bulkUpdateItems").mockResolvedValue({ updated: 2, deleted: 0 })
    vi.spyOn(itemsApi, "bulkDeleteItems").mockResolvedValue({ updated: 0, deleted: 2 })
  })

  it("confirms and bulk deletes selected items", async () => {
    renderClient()

    fireEvent.click(await screen.findByRole("checkbox", { name: "Select all items" }))
    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }))
    fireEvent.click(screen.getByRole("button", { name: "Delete 2 items" }))

    await waitFor(() => {
      expect(itemsApi.bulkDeleteItems).toHaveBeenCalledWith(
        { item_ids: ["item-1", "item-2"] },
        "jwt",
      )
    })
  })

  it("bulk replaces tags for selected items", async () => {
    renderClient()

    fireEvent.click(await screen.findByRole("checkbox", { name: "Select Router" }))
    fireEvent.change(screen.getByLabelText("Bulk tags"), {
      target: { value: "packed, ready" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Apply tags" }))

    await waitFor(() => {
      expect(itemsApi.bulkUpdateItems).toHaveBeenCalledWith(
        {
          item_ids: ["item-1"],
          tag_names: ["packed", "ready"],
          tag_mode: "replace",
        },
        "jwt",
      )
    })
  })

  it("bulk moves selected items to a location", async () => {
    renderClient()

    fireEvent.click(await screen.findByRole("checkbox", { name: "Select Router" }))
    fireEvent.change(screen.getByLabelText("Move selected to"), {
      target: { value: "7" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Move" }))

    await waitFor(() => {
      expect(itemsApi.bulkUpdateItems).toHaveBeenCalledWith(
        {
          item_ids: ["item-1"],
          location_id: 7,
          tag_mode: "replace",
        },
        "jwt",
      )
    })
  })

  it("links selected items to the bulk label print page", async () => {
    renderClient()

    fireEvent.click(await screen.findByRole("checkbox", { name: "Select Router" }))

    expect(screen.getByRole("link", { name: "Print labels" })).toHaveAttribute(
      "href",
      "/items/labels?ids=item-1",
    )
  })
})
