import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { useAuthStore } from "@/lib/auth/auth-store"
import { editPending, getEditingPending, offlineQueue, useOfflineState } from "@/lib/offline/runtime"
import type { PendingItem } from "@/lib/offline/storage"
import messages from "@/messages/zh-TW.json"
import { OfflineStatus, PendingBadge } from "./offline-status"
import { PendingItems } from "./pending-items"

const push = vi.hoisted(() => vi.fn())
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }))
const row: PendingItem = {
  client_id: "key", owner_user_id: "owner", created_at: "2026-11-14T00:00:00Z",
  status: "failed", error_code: "location", attempts: 0, trackBatches: false, customFields: [],
  values: { name: "離線物品", quantity: 1, category_id: null, location_id: 9, image_id: null, tag_names: [], custom_values: {} },
}
function wrapper(children: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}><NextIntlClientProvider locale="zh-TW" messages={messages}>{children}</NextIntlClientProvider></QueryClientProvider>
}
beforeEach(() => {
  push.mockClear()
  useAuthStore.setState({ accessToken: "token", user: { id: "owner" } as never })
  useOfflineState.setState({ rows: [row], error: null })
})
afterEach(() => { vi.restoreAllMocks(); useAuthStore.getState().clear(); useOfflineState.setState({ rows: [], error: null }) })

it("外框在載入、登入與 online 事件同步，離線提示有 live region", async () => {
  const sync = vi.spyOn(offlineQueue, "sync").mockResolvedValue()
  vi.spyOn(offlineQueue.storage, "list").mockResolvedValue([])
  render(wrapper(<OfflineStatus />))
  await waitFor(() => expect(sync).toHaveBeenCalledTimes(1))
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
  fireEvent(window, new Event("offline"))
  expect(screen.getByText(messages.offline.banner).parentElement).toHaveAttribute("aria-live", "polite")
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(true)
  fireEvent(window, new Event("online"))
  expect(screen.queryByText(messages.offline.banner)).not.toBeInTheDocument()
  expect(sync).toHaveBeenCalledTimes(2)
  act(() => useAuthStore.getState().clear())
  fireEvent(window, new Event("online"))
  expect(sync).toHaveBeenCalledTimes(2)
  act(() => useAuthStore.setState({ accessToken: "again", user: { id: "owner" } as never }))
  await waitFor(() => expect(sync).toHaveBeenCalledTimes(3))
})
it("徽章與待同步資料只顯示目前使用者", () => {
  const view = render(wrapper(<><PendingBadge /><PendingItems /></>))
  expect(screen.getByRole("region", { name: "1 筆待同步" })).toBeInTheDocument()
  act(() => useAuthStore.setState({ user: { id: "other" } as never }))
  expect(screen.queryByRole("region")).not.toBeInTheDocument()
  expect(view.container.textContent).toBe("")
})
it("失敗原因可讀、編輯後重送只經記憶體傳遞", () => {
  render(wrapper(<PendingItems />))
  fireEvent.click(screen.getByText(messages.offline.details))
  expect(screen.getByText(messages.offline.reason.location)).toBeVisible()
  fireEvent.click(screen.getByRole("button", { name: messages.offline.edit }))
  expect(push).toHaveBeenCalledWith("/items/new")
  expect(getEditingPending("owner")?.values.location_id).toBe(9)
  expect(getEditingPending("other")).toBeNull()
})
it("捨棄須確認，取消不刪除", async () => {
  const remove = vi.spyOn(offlineQueue, "remove").mockResolvedValue()
  render(wrapper(<PendingItems />))
  fireEvent.click(screen.getByText(messages.offline.details))
  fireEvent.click(screen.getByRole("button", { name: messages.offline.discard }))
  expect(remove).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole("button", { name: messages.offline.cancel }))
  expect(remove).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole("button", { name: messages.offline.discard }))
  fireEvent.click(screen.getByRole("alertdialog").querySelector("button:last-child")!)
  await waitFor(() => expect(remove).toHaveBeenCalledWith("key"))
})
it("viewer 不提供編輯後重送，登入他人無法取得編輯草稿", () => {
  editPending(row)
  useAuthStore.setState({ user: { id: "owner", is_read_only: true } as never })
  render(wrapper(<PendingItems />))
  fireEvent.click(screen.getByText(messages.offline.details))
  expect(screen.queryByRole("button", { name: messages.offline.edit })).not.toBeInTheDocument()
  expect(getEditingPending("other")).toBeNull()
})
