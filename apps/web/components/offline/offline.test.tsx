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
function wrapper(children: React.ReactNode, client = new QueryClient()) {
  return <QueryClientProvider client={client}><NextIntlClientProvider locale="zh-TW" messages={messages}>{children}</NextIntlClientProvider></QueryClientProvider>
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


it.each(["update", "delete"] as const)("衝突 %s 顯示動作、目前內容與明確重送選擇", async (kind) => {
  const conflict: PendingItem = { ...row, kind, item_id: "item", status: "conflict", error_code: "item_modified", server: { id: "item", name: "server", updated_at: "new" } }
  useOfflineState.setState({ rows: [conflict] })
  const resolve = vi.spyOn(offlineQueue, "resolveConflict").mockResolvedValue()
  const sync = vi.spyOn(offlineQueue, "sync").mockResolvedValue()
  const qc = new QueryClient()
  render(wrapper(<PendingItems />, qc))
  fireEvent.click(screen.getByText(messages.offline.details))
  expect(screen.getByText(messages.offline.action[kind])).toBeVisible()
  expect(screen.getByText(messages.offline.reason.item_modified)).toBeVisible()
  expect(screen.queryByRole("button", { name: messages.offline.edit })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: messages.offline.viewCurrent }))
  expect(push).toHaveBeenCalledWith("/items/item")
  expect(qc.getQueryData(["items", "item"])).toMatchObject({ name: "server" })
  fireEvent.click(screen.getByRole("button", { name: kind === "delete" ? messages.offline.deleteAnyway : messages.offline.useMine }))
  await waitFor(() => expect(resolve).toHaveBeenCalledWith(conflict))
  await waitFor(() => expect(sync).toHaveBeenCalled())
})
it.each(["update", "delete"] as const)("捨棄 %s 後重新取得詳情及清單，恢復畫面", async (kind) => {
  useOfflineState.setState({ rows: [{ ...row, kind, item_id: "item" }] })
  const remove = vi.spyOn(offlineQueue, "remove").mockResolvedValue()
  const qc = new QueryClient()
  const invalidate = vi.spyOn(qc, "invalidateQueries")
  render(wrapper(<PendingItems />, qc))
  fireEvent.click(screen.getByText(messages.offline.details))
  fireEvent.click(screen.getByRole("button", { name: messages.offline.discard }))
  fireEvent.click(screen.getByRole("alertdialog").querySelector("button:last-child")!)
  await waitFor(() => expect(remove).toHaveBeenCalledWith("key"))
  await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["items"], refetchType: "all" }))
})
it("失敗的修改可帶原值進編輯頁；刪除沒有編輯入口", () => {
  useOfflineState.setState({ rows: [{ ...row, kind: "update", item_id: "item" }] })
  const view = render(wrapper(<PendingItems />))
  fireEvent.click(screen.getByText(messages.offline.details))
  fireEvent.click(screen.getByRole("button", { name: messages.offline.edit }))
  expect(push).toHaveBeenCalledWith("/items/item/edit")
  expect(getEditingPending("owner")?.values).toEqual(row.values)
  view.unmount()
  useOfflineState.setState({ rows: [{ ...row, kind: "delete", item_id: "item" }] })
  render(wrapper(<PendingItems />))
  fireEvent.click(screen.getByText(messages.offline.details))
  expect(screen.queryByRole("button", { name: messages.offline.edit })).not.toBeInTheDocument()
})
it("背景同步訊息重新讀佇列並更新相關查詢，其他訊息不處理", async () => {
  const target = new EventTarget()
  Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: target })
  vi.spyOn(offlineQueue, "sync").mockResolvedValue()
  const list = vi.spyOn(offlineQueue.storage, "list").mockResolvedValue([])
  const qc = new QueryClient()
  const invalidate = vi.spyOn(qc, "invalidateQueries")
  try {
    render(wrapper(<OfflineStatus />, qc))
    await waitFor(() => expect(list).toHaveBeenCalledTimes(1))
    target.dispatchEvent(new MessageEvent("message", { data: { type: "unrelated" } }))
    expect(list).toHaveBeenCalledTimes(1)
    target.dispatchEvent(new MessageEvent("message", { data: { type: "ims-offline-synced" } }))
    await waitFor(() => expect(list).toHaveBeenCalledTimes(2))
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["items"] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["tags"] })
  } finally { Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: undefined }) }
})
it("其他分頁同步完成時跟著重新讀佇列；自己同步完會通知其他分頁", async () => {
  const list = vi.spyOn(offlineQueue.storage, "list").mockResolvedValue([])
  const sync = vi.spyOn(offlineQueue, "sync").mockImplementation(async (_session, report) => { report({ synced: 1, failed: 0, partial: [] }) })
  const qc = new QueryClient()
  const invalidate = vi.spyOn(qc, "invalidateQueries")
  const other = new BroadcastChannel("ims-offline")
  const heard = vi.fn()
  other.addEventListener("message", (event) => heard(event.data))
  try {
    render(wrapper(<OfflineStatus />, qc))
    // 本分頁同步完 → 其他分頁收到通知
    await waitFor(() => expect(sync).toHaveBeenCalled())
    await waitFor(() => expect(heard).toHaveBeenCalledWith({ type: "ims-offline-synced" }))
    // 其他分頁同步完 → 本分頁重新讀佇列並更新查詢
    const before = list.mock.calls.length
    invalidate.mockClear()
    other.postMessage({ type: "ims-offline-synced" })
    await waitFor(() => expect(list.mock.calls.length).toBeGreaterThan(before))
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["items"] })
  } finally { other.close() }
})
it("App 載入仍有待送項目時註冊背景同步", async () => {
  const register = vi.fn().mockResolvedValue(undefined)
  const worker = Object.assign(new EventTarget(), { getRegistration: vi.fn().mockResolvedValue({ sync: { register } }) })
  Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: worker })
  vi.spyOn(offlineQueue, "sync").mockResolvedValue()
  vi.spyOn(offlineQueue.storage, "list").mockResolvedValue([{ ...row, status: "pending" }])
  try {
    render(wrapper(<OfflineStatus />))
    await waitFor(() => expect(register).toHaveBeenCalledWith("ims-offline-sync"))
  } finally { Object.defineProperty(navigator, "serviceWorker", { configurable: true, value: undefined }) }
})
