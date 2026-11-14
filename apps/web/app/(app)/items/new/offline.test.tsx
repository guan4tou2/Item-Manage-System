import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { toast } from "sonner"
import { saveItemCustomValues } from "@/lib/api/customization"
import { ApiError, NetworkError } from "@/lib/api/client"
import { useAuthStore } from "@/lib/auth/auth-store"
import { offlineQueue } from "@/lib/offline/runtime"
import { OfflineStorageError } from "@/lib/offline/storage"
import messages from "@/messages/zh-TW.json"
import NewItemPage from "./page"

const mocks = vi.hoisted(() => ({ push: vi.fn(), create: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }), useSearchParams: () => new URLSearchParams() }))
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }))
vi.mock("@/components/ai/batch-entry-card", () => ({ BatchEntryCard: () => <div>AI</div> }))
vi.mock("@/components/items/item-form", () => ({
  ItemForm: ({ onSubmit }: { onSubmit: (values: unknown) => void }) => <button onClick={() => onSubmit({ name: "物品", quantity: 1, category_id: null, location_id: null, image_id: "已上傳圖片", tag_names: [], custom_values: {} })}>送出</button>,
}))
vi.mock("@/lib/hooks/use-items", () => ({ useCreateItem: () => ({ mutateAsync: mocks.create, isPending: false }) }))
vi.mock("@/lib/hooks/use-categories", () => ({ useCategories: () => ({ data: [] }) }))
vi.mock("@/lib/hooks/use-locations", () => ({ useLocations: () => ({ data: [] }) }))
vi.mock("@/lib/hooks/use-tags", () => ({ useTags: () => ({ data: [] }) }))
vi.mock("@/lib/api/customization", () => ({ listCustomFields: vi.fn(async () => []), listItemTemplates: vi.fn(async () => []), saveItemCustomValues: vi.fn() }))

function renderPage() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><NextIntlClientProvider locale="zh-TW" messages={messages}><NewItemPage /></NextIntlClientProvider></QueryClientProvider>)
}
beforeEach(() => {
  vi.clearAllMocks()
  useAuthStore.setState({ accessToken: "token", user: { id: "owner" } as never })
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
})
afterEach(() => { vi.restoreAllMocks(); useAuthStore.getState().clear() })

it("D7 離線保存完整資料（含已上傳圖片）後回清單", async () => {
  const save = vi.spyOn(offlineQueue, "save").mockResolvedValue()
  renderPage()
  fireEvent.click(screen.getByText("送出"))
  await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/items"))
  expect(mocks.create).not.toHaveBeenCalled()
  expect(save).toHaveBeenCalledWith(expect.objectContaining({ owner_user_id: "owner", status: "pending", values: expect.objectContaining({ image_id: "已上傳圖片" }) }))
  expect(toast.success).toHaveBeenCalledWith(messages.offline.saved)
})
it("D7 fetch 例外才轉入離線佇列", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(true)
  mocks.create.mockRejectedValue(new NetworkError(new Error("fetch")))
  const save = vi.spyOn(offlineQueue, "save").mockResolvedValue()
  renderPage()
  fireEvent.click(screen.getByText("送出"))
  await waitFor(() => expect(save).toHaveBeenCalledTimes(1))
  expect(mocks.push).toHaveBeenCalledWith("/items")
})
it.each([422, 500])("D7 HTTP %i 沿用錯誤提示，不入列", async (status) => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(true)
  mocks.create.mockRejectedValue(new ApiError(status, null))
  const save = vi.spyOn(offlineQueue, "save").mockResolvedValue()
  renderPage()
  fireEvent.click(screen.getByText("送出"))
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith(messages.items.toast.saveFailed))
  expect(save).not.toHaveBeenCalled()
  expect(mocks.push).not.toHaveBeenCalled()
})
it.each(["unavailable", "quota"] as const)("D17 %s 顯示明確錯誤並留在表單", async (code) => {
  vi.spyOn(offlineQueue, "save").mockRejectedValue(new OfflineStorageError(code))
  renderPage()
  fireEvent.click(screen.getByText("送出"))
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith(messages.offline[code]))
  expect(mocks.push).not.toHaveBeenCalled()
  expect(screen.getByText("送出")).toBeInTheDocument()
})


it("共用送出後，線上自訂欄位失敗仍沿用原本錯誤回饋並保留表單", async () => {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(true)
  mocks.create.mockResolvedValue({ id: "created" })
  vi.mocked(saveItemCustomValues).mockRejectedValueOnce(new Error("自訂欄位失敗"))
  const save = vi.spyOn(offlineQueue, "save").mockResolvedValue()
  renderPage()
  fireEvent.click(screen.getByText("送出"))
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith(messages.items.toast.saveFailed))
  expect(mocks.push).not.toHaveBeenCalled()
  expect(save).not.toHaveBeenCalled()
  expect(mocks.create).toHaveBeenCalledTimes(1)
})
