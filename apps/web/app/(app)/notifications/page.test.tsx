import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { NotificationListResponse, NotificationRead } from "@/lib/api/notifications"
import enMessages from "@/messages/en.json"

import NotificationsPage from "./page"

const mocks = vi.hoisted(() => ({
  createRestockListFromLowStockItems: vi.fn(),
  deleteMutate: vi.fn(),
  markAllMutate: vi.fn(),
  markReadMutateAsync: vi.fn(),
  push: vi.fn(),
  notifications: {
    items: [] as NotificationRead[],
    total: 0,
    unread_count: 0,
  } as NotificationListResponse,
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/lists", () => ({
  createRestockListFromLowStockItems: mocks.createRestockListFromLowStockItems,
}))

vi.mock("@/lib/hooks/use-notifications", () => ({
  useNotifications: () => ({ isLoading: false, data: mocks.notifications }),
  useMarkNotificationRead: () => ({
    isPending: false,
    mutateAsync: mocks.markReadMutateAsync,
  }),
  useMarkAllNotificationsRead: () => ({
    isPending: false,
    mutate: mocks.markAllMutate,
  }),
  useDeleteNotification: () => ({
    mutate: mocks.deleteMutate,
  }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const lowStockRow: NotificationRead = {
  id: "id-1",
  user_id: "u1",
  type: "low_stock",
  title: "「牙膏」庫存不足",
  body: "目前數量：1，提醒閾值：2",
  link: "/items/item-1",
  read_at: null,
  created_at: new Date().toISOString(),
}

function renderPage() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <NotificationsPage />
    </NextIntlClientProvider>,
  )
}

describe("NotificationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.notifications = {
      items: [lowStockRow],
      total: 1,
      unread_count: 1,
    }
    mocks.markReadMutateAsync.mockResolvedValue({
      ...lowStockRow,
      read_at: new Date().toISOString(),
    })
    mocks.createRestockListFromLowStockItems.mockResolvedValue({
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

  it("marks unread notifications read before navigating", async () => {
    let resolveRead: (value: NotificationRead) => void = () => undefined
    mocks.markReadMutateAsync.mockImplementation(
      () =>
        new Promise<NotificationRead>((resolve) => {
          resolveRead = resolve
        }),
    )

    renderPage()

    fireEvent.click(screen.getByRole("button", { name: /open notification/i }))

    expect(screen.getByRole("listitem", { name: /牙膏/ })).toHaveAttribute(
      "aria-busy",
      "true",
    )
    expect(mocks.push).not.toHaveBeenCalled()

    resolveRead({ ...lowStockRow, read_at: new Date().toISOString() })

    await waitFor(() => {
      expect(mocks.markReadMutateAsync).toHaveBeenCalledWith("id-1")
      expect(mocks.push).toHaveBeenCalledWith("/items/item-1")
    })
  })

  it("opens already-read notifications without marking read again", () => {
    mocks.notifications = {
      items: [{ ...lowStockRow, read_at: new Date().toISOString() }],
      total: 1,
      unread_count: 0,
    }

    renderPage()

    fireEvent.click(screen.getByRole("button", { name: /open notification/i }))

    expect(mocks.markReadMutateAsync).not.toHaveBeenCalled()
    expect(mocks.push).toHaveBeenCalledWith("/items/item-1")
  })

  it("creates a restock list from a low-stock notification", async () => {
    renderPage()

    fireEvent.click(screen.getByRole("button", { name: "Add to restock list" }))

    await waitFor(() => {
      expect(mocks.createRestockListFromLowStockItems).toHaveBeenCalledWith(
        [
          {
            item_id: "item-1",
            name: "牙膏",
            quantity: 1,
            min_quantity: 2,
            deficit: 1,
          },
        ],
        "jwt",
        expect.objectContaining({
          title: expect.stringMatching(/^Restock /),
        }),
      )
      expect(mocks.push).toHaveBeenCalledWith("/lists/list-1")
    })
  })
})
