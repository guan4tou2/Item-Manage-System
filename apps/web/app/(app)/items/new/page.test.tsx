import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"
import type { ItemFormValues } from "@/components/items/item-form"

import NewItemPage from "./page"

const createItemMock = vi.hoisted(() => vi.fn())
const draftCountsMock = vi.hoisted(() => vi.fn())

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

vi.mock("@/lib/hooks/use-ai-drafts", () => ({
  useDraftCounts: () => draftCountsMock(),
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

const zeroCounts = {
  pending: 0,
  processing: 0,
  ready: 0,
  failed: 0,
  accepted: 0,
  discarded: 0,
}

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
    draftCountsMock.mockReturnValue({ data: zeroCounts, isLoading: false, isError: false })
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

describe("NewItemPage read-only viewer (Phase 30)", () => {
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("blocks the create form for viewers and links back", async () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "viewer-1", is_read_only: true } as never,
    })
    renderPage()

    expect(await screen.findByTestId("viewer-notice")).toBeInTheDocument()
    expect(screen.getByText("Viewers cannot edit")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "submit-item" })).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to items list" })).toHaveAttribute(
      "href",
      "/items",
    )
  })

  it("renders the form for writers (zero regression)", async () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "writer-1", is_read_only: false } as never,
    })
    renderPage()

    expect(await screen.findByRole("button", { name: "submit-item" })).toBeInTheDocument()
    expect(screen.queryByTestId("viewer-notice")).not.toBeInTheDocument()
  })
})

describe("NewItemPage AI batch intake entry (Phase 32)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "writer-1", is_read_only: false } as never,
    })
    draftCountsMock.mockReturnValue({ data: zeroCounts, isLoading: false, isError: false })
  })

  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("offers the batch intake entry card next to the manual form", async () => {
    renderPage()

    expect(await screen.findByTestId("batch-entry-card")).toBeInTheDocument()
    expect(screen.getByText("AI batch intake")).toBeInTheDocument()
    expect(
      screen.getByText(
        "Upload several photos; each one is recognized in turn with category, location, and tag suggestions.",
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open draft queue" })).toHaveAttribute(
      "href",
      "/items/drafts",
    )
  })

  it("badges the number of drafts awaiting review", async () => {
    draftCountsMock.mockReturnValue({
      data: { ...zeroCounts, pending: 2, processing: 1, ready: 3, failed: 1, accepted: 9 },
      isLoading: false,
      isError: false,
    })
    renderPage()

    expect(await screen.findByTestId("batch-entry-badge")).toHaveTextContent("7 awaiting review")
  })

  it("hides the badge when nothing awaits review", async () => {
    renderPage()

    expect(await screen.findByTestId("batch-entry-card")).toBeInTheDocument()
    expect(screen.queryByTestId("batch-entry-badge")).not.toBeInTheDocument()
  })

  it("keeps the entry usable when the counts query fails", async () => {
    draftCountsMock.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    renderPage()

    expect(await screen.findByTestId("batch-entry-card")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open draft queue" })).toBeInTheDocument()
    expect(screen.queryByTestId("batch-entry-badge")).not.toBeInTheDocument()
  })

  it("shows a checking hint while the counts load", async () => {
    draftCountsMock.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    renderPage()

    expect(await screen.findByTestId("batch-entry-card")).toBeInTheDocument()
    expect(screen.getByText("Checking…")).toBeInTheDocument()
    expect(screen.queryByTestId("batch-entry-badge")).not.toBeInTheDocument()
  })

  it("hides the entry from viewers", async () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "viewer-1", is_read_only: true } as never,
    })
    renderPage()

    expect(await screen.findByTestId("viewer-notice")).toBeInTheDocument()
    expect(screen.queryByTestId("batch-entry-card")).not.toBeInTheDocument()
  })
})
