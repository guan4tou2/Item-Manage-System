import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import type { ItemFormValues } from "@/components/items/item-form"

import NewItemPage from "./page"

const createItemMock = vi.hoisted(() => vi.fn())

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/components/items/item-form", () => ({
  ItemForm: (props: {
    itemTemplates?: Array<{ id: number; name: string }>
    onSubmit: (values: ItemFormValues) => void | Promise<void>
    onTrackBatchesChange?: (value: boolean) => void
  }) => (
    <div>
      {(props.itemTemplates ?? []).map((template) => (
        <button key={template.id} type="button">
          {template.name}
        </button>
      ))}
      <button type="button" onClick={() => props.onTrackBatchesChange?.(true)}>
        enable-tracking
      </button>
      <button
        type="button"
        onClick={() =>
          void props.onSubmit({
            name: "New thing",
            description: "",
            category_id: null,
            location_id: null,
            quantity: 4,
            notes: "",
            image_id: null,
            tag_names: [],
            custom_values: {},
          })
        }
      >
        submit-item
      </button>
    </div>
  ),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/hooks/use-categories", () => ({
  useCategories: () => ({ data: [] }),
}))

vi.mock("@/lib/hooks/use-items", () => ({
  useCreateItem: () => ({ isPending: false, mutateAsync: createItemMock }),
}))

vi.mock("@/lib/hooks/use-locations", () => ({
  useLocations: () => ({ data: [] }),
}))

vi.mock("@/lib/hooks/use-tags", () => ({
  useTags: () => ({ data: [] }),
}))

vi.mock("@/lib/api/batches", () => ({
  createBatch: vi.fn(),
}))

vi.mock("@/lib/api/customization", () => ({
  listCustomFields: vi.fn().mockResolvedValue([]),
  listItemTemplates: vi.fn().mockResolvedValue([
    {
      id: 10,
      name: "Restock pack",
      payload: { name: "AA Battery", quantity: 12 },
      created_at: "2026-06-19T00:00:00Z",
    },
  ]),
  saveItemCustomValues: vi.fn(),
}))

import * as batchApi from "@/lib/api/batches"

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <NewItemPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("NewItemPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("passes item templates into the item form", async () => {
    renderPage()

    expect(await screen.findByRole("button", { name: "Restock pack" })).toBeInTheDocument()
  })

  it("creates the item first, then the first batch when tracking is on", async () => {
    const order: string[] = []
    createItemMock.mockImplementation(async () => {
      order.push("item")
      return { id: "item-9" }
    })
    vi.mocked(batchApi.createBatch).mockImplementation(async () => {
      order.push("batch")
      return {} as never
    })

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "enable-tracking" }))
    fireEvent.click(screen.getByRole("button", { name: "submit-item" }))

    await waitFor(() => expect(batchApi.createBatch).toHaveBeenCalled())
    expect(batchApi.createBatch).toHaveBeenCalledWith("item-9", {}, "jwt")
    expect(order).toEqual(["item", "batch"])
  })

  it("surfaces a toast when the first batch fails", async () => {
    createItemMock.mockResolvedValue({ id: "item-9" })
    vi.mocked(batchApi.createBatch).mockRejectedValue(new Error("boom"))

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "enable-tracking" }))
    fireEvent.click(screen.getByRole("button", { name: "submit-item" }))

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalled())
  })

  it("skips batch creation when tracking stays off", async () => {
    createItemMock.mockResolvedValue({ id: "item-9" })

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "submit-item" }))

    await waitFor(() => expect(createItemMock).toHaveBeenCalled())
    expect(batchApi.createBatch).not.toHaveBeenCalled()
  })
})
