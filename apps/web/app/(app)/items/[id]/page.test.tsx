import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import * as customizationApi from "@/lib/api/customization"
import enMessages from "@/messages/en.json"

import ItemDetailPage from "./page"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "item-1" }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/components/collaboration/loan-card", () => ({
  LoanCard: () => <div>Loan card</div>,
}))

vi.mock("@/components/collaboration/new-transfer-dialog", () => ({
  NewTransferDialog: () => <button type="button">Transfer</button>,
}))

vi.mock("@/components/items/delete-item-dialog", () => ({
  DeleteItemDialog: () => <button type="button">Delete</button>,
}))

vi.mock("@/components/items/favorite-button", () => ({
  FavoriteButton: () => <button type="button">Favorite</button>,
}))

const authState = { user: { id: "owner-1", is_read_only: false } }

vi.mock("@/lib/auth/auth-store", () => ({
  useAuthStore: (selector: (state: { user: { id: string; is_read_only: boolean } }) => unknown) =>
    selector(authState),
}))

vi.mock("@/components/items/batch-section", () => ({
  BatchSection: ({ canEdit }: { canEdit: boolean }) => (
    <div data-testid="batch-section" data-can-edit={String(canEdit)} />
  ),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/hooks/use-items", () => ({
  useDeleteItem: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useItem: () => ({
    data: {
      id: "item-1",
      name: "Network switch",
      description: "Rack switch",
      barcode: "4710085200016",
      quantity: 2,
      min_quantity: null,
      notes: "Keep warranty card",
      is_favorite: false,
      track_batches: true,
      image_id: null,
      warehouse_id: null,
      owner_id: "owner-1",
      owner_username: "owner",
      created_at: "2026-06-19T00:00:00Z",
      updated_at: "2026-06-19T00:00:00Z",
      category: null,
      location: {
        id: 4,
        parent_id: 3,
        name: "抽屜",
        kind: null,
        sort_order: 0,
        floor_plan_image_id: null,
        path: "1F / 廚房 / 上櫃 / 抽屜",
      },
      tags: [
        { id: 1, name: "network" },
        { id: 2, name: "rack" },
      ],
    },
    isError: false,
    isLoading: false,
  }),
}))

vi.mock("@/lib/api/customization", () => ({
  createItemTemplate: vi.fn().mockResolvedValue({
    id: 10,
    name: "Network switch template",
    payload: {},
    created_at: "2026-06-19T00:00:00Z",
  }),
  listCustomFields: vi.fn().mockResolvedValue([
    { id: 7, name: "Serial number", field_type: "text", created_at: "2026-06-19T00:00:00Z" },
  ]),
  listItemCustomValues: vi.fn().mockResolvedValue([
    { custom_field_id: 7, value: "SN-123" },
  ]),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ItemDetailPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("ItemDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("saves the current item as a reusable template", async () => {
    renderPage()

    expect(await screen.findByText("SN-123")).toBeInTheDocument()
    const saveAsTemplateButton = screen.getByRole("button", { name: "Save as template" })
    expect(saveAsTemplateButton.parentElement).toHaveClass("flex-wrap")
    fireEvent.click(saveAsTemplateButton)

    await waitFor(() => {
      expect(customizationApi.createItemTemplate).toHaveBeenCalledWith(
        {
          name: "Network switch template",
          payload: {
            name: "Network switch",
            description: "Rack switch",
            quantity: 2,
            notes: "Keep warranty card",
            tag_names: ["network", "rack"],
            custom_values: {
              "7": "SN-123",
            },
          },
        },
        "jwt",
      )
    })
  })

  it("copies the barcode to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    })

    renderPage()

    expect(await screen.findByText("4710085200016")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Copy barcode" }))

    await waitFor(() => expect(writeText).toHaveBeenCalledWith("4710085200016"))
  })

  it("shows the location breadcrumb truncated in the middle", async () => {
    renderPage()

    const path = await screen.findByTestId("item-location-path")
    expect(path).toHaveTextContent("…")
    expect(path).toHaveAttribute("title", "1F / 廚房 / 上櫃 / 抽屜")
  })

})

describe("ItemDetailPage read-only viewer (Phase 30)", () => {
  beforeEach(() => {
    authState.user = { id: "owner-1", is_read_only: true }
  })

  afterEach(() => {
    authState.user = { id: "owner-1", is_read_only: false }
  })

  it("hides all write actions and shows the sticky viewer notice", async () => {
    renderPage()

    expect(await screen.findByTestId("viewer-item-notice")).toHaveTextContent(
      "You are a viewer",
    )
    expect(screen.queryByRole("button", { name: "Favorite" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Transfer" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Save as template" }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Edit" })).not.toBeInTheDocument()
    expect(screen.queryByText("Loan card")).not.toBeInTheDocument()
    expect(screen.getByTestId("batch-section")).toHaveAttribute("data-can-edit", "false")
    // 列印標籤為讀取性操作，維持可用（登錄決策）
    expect(screen.getByRole("link", { name: "Print label" })).toBeInTheDocument()
  })

  it("keeps all write actions for writers (zero regression)", async () => {
    authState.user = { id: "owner-1", is_read_only: false }
    renderPage()

    expect(await screen.findByRole("link", { name: "Edit" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Favorite" })).toBeInTheDocument()
    expect(screen.getByText("Loan card")).toBeInTheDocument()
    expect(screen.getByTestId("batch-section")).toHaveAttribute("data-can-edit", "true")
    expect(screen.queryByTestId("viewer-item-notice")).not.toBeInTheDocument()
  })
})
