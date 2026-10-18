import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import * as listsApi from "@/lib/api/lists"
import type { LowStockItem } from "@/lib/api/stats"
import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import { LowStockCard } from "./low-stock-card"

const push = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock("@/lib/api/lists", () => ({
  createRestockListFromLowStockItems: vi.fn(),
}))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const lowStockItems: LowStockItem[] = [
  {
    item_id: "item-1",
    name: "Batteries",
    quantity: 1,
    min_quantity: 5,
    deficit: 4,
  },
]

describe("LowStockCard", () => {
  beforeEach(() => {
    push.mockReset()
    vi.mocked(listsApi.createRestockListFromLowStockItems).mockResolvedValue({
      id: "list-1",
      kind: "shopping",
      title: "Restock",
      description: null,
      start_date: null,
      end_date: null,
      budget: null,
      entry_count: 1,
      done_count: 0,
      created_at: "2026-06-23T00:00:00Z",
      updated_at: "2026-06-23T00:00:00Z",
    })
  })

  it("does not show the restock CTA when low stock is empty", () => {
    render(<LowStockCard items={[]} />, { wrapper: Provider })

    expect(screen.queryByRole("button", { name: "Create restock list" })).not.toBeInTheDocument()
  })

  it("creates a restock list and opens it", async () => {
    render(<LowStockCard items={lowStockItems} />, { wrapper: Provider })

    fireEvent.click(screen.getByRole("button", { name: "Create restock list" }))

    await waitFor(() => {
      expect(listsApi.createRestockListFromLowStockItems).toHaveBeenCalledWith(
        lowStockItems,
        "jwt",
        expect.objectContaining({
          title: expect.stringMatching(/^Restock /),
        }),
      )
      expect(push).toHaveBeenCalledWith("/lists/list-1")
    })
  })
})

describe("LowStockCard read-only viewer (Phase 30)", () => {
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("hides the restock list entry for viewers", () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "viewer-1", is_read_only: true } as never })
    render(<LowStockCard items={lowStockItems} />, { wrapper: Provider })
    expect(screen.queryByRole("button", { name: "Create restock list" })).not.toBeInTheDocument()
  })

  it("keeps the restock list entry for writers (zero regression)", () => {
    useAuthStore.setState({ accessToken: "jwt", user: { id: "writer-1", is_read_only: false } as never })
    render(<LowStockCard items={lowStockItems} />, { wrapper: Provider })
    expect(screen.getByRole("button", { name: "Create restock list" })).toBeInTheDocument()
  })
})
