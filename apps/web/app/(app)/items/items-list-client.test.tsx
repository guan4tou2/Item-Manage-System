import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { ItemRead } from "@/lib/api/items"
import * as batchesApi from "@/lib/api/batches"
import * as itemsApi from "@/lib/api/items"
import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"
import { toast } from "sonner"

import { ItemsListClient } from "./items-list-client"

const replace = vi.fn()
const searchParamsRef = { current: new URLSearchParams() }

vi.mock("next/navigation", () => ({
  usePathname: () => "/items",
  useRouter: () => ({ replace }),
  useSearchParams: () => searchParamsRef.current,
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
      {
        id: 7,
        parent_id: null,
        name: "1F",
        kind: "floor",
        sort_order: 0,
        floor_plan_image_id: null,
        path: "1F",
      },
      {
        id: 8,
        parent_id: null,
        name: "2F",
        kind: "floor",
        sort_order: 1,
        floor_plan_image_id: null,
        path: "2F",
      },
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
    searchParamsRef.current = new URLSearchParams()
    vi.restoreAllMocks()
    vi.spyOn(itemsApi, "listItems").mockResolvedValue({
      items: [item("item-1", "Router"), item("item-2", "Switch")],
      total: 2,
      page: 1,
      per_page: 20,
    })
    vi.spyOn(itemsApi, "bulkUpdateItems").mockResolvedValue({ updated: 2, deleted: 0 })
    vi.spyOn(itemsApi, "bulkDeleteItems").mockResolvedValue({ updated: 0, deleted: 2 })
    vi.spyOn(batchesApi, "consumeFefo").mockResolvedValue({
      consumed: [{ batch_id: "batch-1", quantity: 1 }],
    } as never)
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

  it("writes the expiry filter and sort when a chip is chosen", async () => {
    renderClient()

    fireEvent.click(await screen.findByRole("button", { name: "Within 7 days" }))

    expect(replace).toHaveBeenCalledWith("/items?expiry=expiring_soon&sort=expiry_asc", {
      scroll: false,
    })
  })

  it("lands in expiry mode from a deep link and consumes FEFO one with clearing feedback", async () => {
    searchParamsRef.current = new URLSearchParams("expiry=expired&sort=expiry_asc")
    vi.spyOn(itemsApi, "listItems").mockResolvedValue({
      items: [
        {
          ...item("item-1", "Milk"),
          quantity: 1,
          track_batches: true,
          soonest_expiry: "2026-10-01",
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
    })

    renderClient()

    fireEvent.click(await screen.findByRole("button", { name: "Consume 1: Milk" }))

    await waitFor(() =>
      expect(batchesApi.consumeFefo).toHaveBeenCalledWith("item-1", { quantity: 1 }, "jwt"),
    )
    await waitFor(() => expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Cleared: Milk"))
    expect(screen.getByTestId("items-list-announce")).toHaveTextContent("Cleared: Milk")
  })
})

describe("ItemsListClient read-only viewer (Phase 30)", () => {
  beforeEach(() => {
    replace.mockReset()
    searchParamsRef.current = new URLSearchParams()
    vi.restoreAllMocks()
    vi.spyOn(itemsApi, "listItems").mockResolvedValue({
      items: [item("item-1", "Router")],
      total: 1,
      page: 1,
      per_page: 20,
    })
  })

  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("hides create entry points and selection for viewers", async () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "viewer-1", is_read_only: true } as never })
    renderClient()

    expect(await screen.findByText("Router")).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "New item" })).not.toBeInTheDocument()
    expect(screen.queryByRole("checkbox", { name: "Select all items" })).not.toBeInTheDocument()
    expect(screen.queryByRole("checkbox", { name: "Select Router" })).not.toBeInTheDocument()
  })

  it("hides the empty-state CTA for viewers", async () => {
    vi.mocked(itemsApi.listItems).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    })
    useAuthStore.setState({ accessToken: "jwt", user: { id: "viewer-1", is_read_only: true } as never })
    renderClient()

    expect(await screen.findByText("No items yet")).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Create your first item" })).not.toBeInTheDocument()
  })

  it("keeps create entry points and selection for writers (zero regression)", async () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "writer-1", is_read_only: false } as never })
    renderClient()

    expect(await screen.findByText("Router")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "New item" })).toBeInTheDocument()
    expect(screen.getByRole("checkbox", { name: "Select all items" })).toBeInTheDocument()
  })
})
