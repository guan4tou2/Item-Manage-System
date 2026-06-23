import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

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

vi.mock("@/lib/auth/auth-store", () => ({
  useAuthStore: (selector: (state: { user: { id: string } }) => unknown) =>
    selector({ user: { id: "owner-1" } }),
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
      quantity: 2,
      min_quantity: null,
      notes: "Keep warranty card",
      is_favorite: false,
      image_id: null,
      warehouse_id: null,
      owner_id: "owner-1",
      owner_username: "owner",
      created_at: "2026-06-19T00:00:00Z",
      updated_at: "2026-06-19T00:00:00Z",
      category: null,
      location: null,
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
})
