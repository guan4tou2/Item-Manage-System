import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"
import type { ItemFormValues } from "@/components/items/item-form"

import EditItemPage from "./page"
import { offlineQueue, clearEditingPending, editPending, useOfflineState } from "@/lib/offline/runtime"
import { ApiError, NetworkError } from "@/lib/api/client"
import { OfflineStorageError, type PendingItem } from "@/lib/offline/storage"

const push = vi.hoisted(() => vi.fn())
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
  useRouter: () => ({ push }),
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
  const view = render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <EditItemPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
  return { ...view, queryClient }
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


describe("Phase 52 offline edit", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearEditingPending()
    useOfflineState.setState({ rows: [], error: null })
    useAuthStore.setState({ user: { id: "user_1", is_read_only: false } as never, accessToken: "jwt" })
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  })
  afterEach(() => { vi.restoreAllMocks(); clearEditingPending(); useOfflineState.setState({ rows: [], error: null }) })
  it("stores an update with the original version, updates item cache and stays on the form without sending", async () => {
    const save = vi.spyOn(offlineQueue, "save").mockResolvedValue()
    const { queryClient } = renderPage()
    fireEvent.click(await screen.findByRole("button", { name: "submit-item" }))
    await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({ kind: "update", item_id: "item-1", base_updated_at: itemFixture.updated_at, owner_user_id: "user_1", values: expect.objectContaining({ name: "Batteries" }) })))
    expect(updateMock).not.toHaveBeenCalled()
    expect(queryClient.getQueryData(["items", "item-1"])).toMatchObject({ name: "Batteries", quantity: 5 })
    expect(toast.success).toHaveBeenCalledWith(enMessages.offline.saved)
    // 離線時導頁需要連線抓頁面資料，會失敗：留在表單上。
    expect(push).not.toHaveBeenCalled()
  })
  it.each(["network", "http"])("only queues %s failure after an online submit", async (kind) => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(true)
    const save = vi.spyOn(offlineQueue, "save").mockResolvedValue()
    updateMock.mockRejectedValueOnce(kind === "network" ? new NetworkError("offline") : new ApiError(422, null))
    renderPage()
    fireEvent.click(await screen.findByRole("button", { name: "submit-item" }))
    await waitFor(() => expect(updateMock).toHaveBeenCalled())
    if (kind === "network") await waitFor(() => expect(save).toHaveBeenCalled())
    else { await waitFor(() => expect(toast.error).toHaveBeenCalledWith(enMessages.items.toast.saveFailed)); expect(save).not.toHaveBeenCalled() }
  })
  it("keeps the form when device storage fails and shows a useful error", async () => {
    vi.spyOn(offlineQueue, "save").mockRejectedValue(new OfflineStorageError("quota"))
    renderPage()
    fireEvent.click(await screen.findByRole("button", { name: "submit-item" }))
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith(enMessages.offline.quota))
    expect(push).not.toHaveBeenCalled()
  })
  it("resending a failed update replaces its identity and original base, and offline tracking does not call the API", async () => {
    const draft: PendingItem = { client_id: "original-key", owner_user_id: "user_1", kind: "update", item_id: "item-1", base_updated_at: "original-base", created_at: "original-date", attempts: 0, error_code: "location", status: "failed", trackBatches: false, customFields: [], values: { name: "offline", quantity: 5, category_id: null, location_id: null, tag_names: [], custom_values: {} } }
    editPending(draft)
    useOfflineState.setState({ rows: [draft] })
    const save = vi.spyOn(offlineQueue, "save").mockResolvedValue()
    renderPage()
    fireEvent.click(await screen.findByRole("button", { name: "enable-tracking" }))
    expect(createBatchMock).not.toHaveBeenCalled()
    expect(screen.getByText(enMessages.offline.unsyncedChanges)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "submit-item" }))
    await waitFor(() => expect(save).toHaveBeenCalledWith(expect.objectContaining({ client_id: "original-key", base_updated_at: "original-base", created_at: "original-date", status: "pending" })))
  })
})
