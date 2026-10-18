import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"
import type { ItemFormValues } from "@/components/items/item-form"

import EditItemPage from "./page"

const updateMock = vi.hoisted(() => vi.fn())
const createBatchMock = vi.hoisted(() => vi.fn())

const itemFixture = {
  id: "item-1",
  name: "Batteries",
  description: null,
  quantity: 5,
  min_quantity: null,
  track_batches: false,
  notes: null,
  is_favorite: false,
  image_id: null,
  warehouse_id: null,
  owner_id: "user_1",
  owner_username: "owner",
  created_at: "2026-06-19T00:00:00Z",
  updated_at: "2026-06-19T00:00:00Z",
  category: null,
  location: null,
  tags: [],
}

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "item-1" }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/components/items/item-form", () => ({
  ItemForm: (props: {
    onSubmit: (values: ItemFormValues) => void | Promise<void>
    trackBatches?: boolean
    trackBatchesLocked?: boolean
    onTrackBatchesChange?: (value: boolean) => void
  }) => (
    <div>
      <span data-testid="tracking">{String(props.trackBatches)}</span>
      <span data-testid="locked">{String(props.trackBatchesLocked)}</span>
      <button type="button" onClick={() => props.onTrackBatchesChange?.(true)}>
        enable-tracking
      </button>
      <button
        type="button"
        onClick={() =>
          void props.onSubmit({
            name: "Batteries",
            description: "",
            category_id: null,
            location_id: null,
            quantity: 5,
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

vi.mock("@/lib/hooks/use-items", () => ({
  useItem: () => ({ data: itemFixture, isLoading: false, isError: false }),
  useUpdateItem: () => ({ isPending: false, mutateAsync: updateMock }),
}))

vi.mock("@/lib/hooks/use-batches", () => ({
  useCreateBatch: () => ({ isPending: false, mutateAsync: createBatchMock }),
}))

vi.mock("@/lib/hooks/use-categories", () => ({
  useCategories: () => ({ data: [] }),
}))

vi.mock("@/lib/hooks/use-locations", () => ({
  useLocations: () => ({ data: [] }),
}))

vi.mock("@/lib/hooks/use-tags", () => ({
  useTags: () => ({ data: [] }),
}))

vi.mock("@/lib/api/customization", () => ({
  listCustomFields: vi.fn().mockResolvedValue([]),
  listItemCustomValues: vi.fn().mockResolvedValue([]),
  saveItemCustomValues: vi.fn(),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <EditItemPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("EditItemPage batch tracking", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    updateMock.mockResolvedValue({})
    createBatchMock.mockResolvedValue({})
  })

  it("posts the first batch immediately when tracking is enabled", async () => {
    renderPage()

    fireEvent.click(await screen.findByRole("button", { name: "enable-tracking" }))

    await waitFor(() => expect(createBatchMock).toHaveBeenCalledWith({}))
    await waitFor(() => expect(screen.getByTestId("tracking")).toHaveTextContent("true"))
    expect(screen.getByTestId("locked")).toHaveTextContent("true")
    expect(vi.mocked(toast.success)).toHaveBeenCalled()
  })

  it("omits quantity from the update body while tracking", async () => {
    renderPage()

    fireEvent.click(await screen.findByRole("button", { name: "enable-tracking" }))
    await waitFor(() => expect(screen.getByTestId("tracking")).toHaveTextContent("true"))

    fireEvent.click(screen.getByRole("button", { name: "submit-item" }))

    await waitFor(() => expect(updateMock).toHaveBeenCalled())
    const body = updateMock.mock.calls[0]?.[0] as Record<string, unknown>
    expect("quantity" in body).toBe(false)
  })

  it("keeps quantity in the update body for untracked items", async () => {
    renderPage()

    fireEvent.click(await screen.findByRole("button", { name: "submit-item" }))

    await waitFor(() => expect(updateMock).toHaveBeenCalled())
    const body = updateMock.mock.calls[0]?.[0] as Record<string, unknown>
    expect(body.quantity).toBe(5)
  })

  it("shows a toast and stays untracked when enabling fails", async () => {
    createBatchMock.mockRejectedValue(new Error("boom"))

    renderPage()

    fireEvent.click(await screen.findByRole("button", { name: "enable-tracking" }))

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalled())
    expect(screen.getByTestId("tracking")).toHaveTextContent("false")
  })
})

describe("EditItemPage read-only viewer (Phase 30)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    updateMock.mockResolvedValue({})
  })

  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("blocks the edit form for viewers and links back to the item", async () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "viewer-1", is_read_only: true } as never,
    })
    renderPage()

    expect(await screen.findByTestId("viewer-notice")).toBeInTheDocument()
    expect(screen.getByText("Viewers cannot edit")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "submit-item" })).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to item" })).toHaveAttribute(
      "href",
      "/items/item-1",
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
