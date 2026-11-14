import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/ai-receipts", () => ({
  createReceipt: vi.fn(),
  getReceipt: vi.fn(),
  putReceiptReview: vi.fn(),
  deleteReceiptReview: vi.fn(),
}))

import * as api from "@/lib/api/ai-receipts"
import type { DraftListResponse } from "@/lib/api/ai-drafts"
import { useCreateReceipt, useReceipt, useReceiptReview } from "./use-ai-receipts"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const response: api.ReceiptCreateResponse = {
  receipt_id: "receipt-1",
  truncated: false,
  created: [],
}

describe("useCreateReceipt", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.token = "jwt"
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
  })

  it("creates a receipt and invalidates the drafts cache", async () => {
    vi.mocked(api.createReceipt).mockResolvedValue(response)
    const spy = vi.spyOn(queryClient, "invalidateQueries")

    const { result } = renderHook(() => useCreateReceipt(), { wrapper })
    result.current.mutate(["page-1", "page-2"])

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.createReceipt).toHaveBeenCalledWith(["page-1", "page-2"], "jwt")
    expect(spy.mock.calls.map((call) => call[0]?.queryKey)).toContainEqual(["ai-drafts"])
  })

  it("exposes the failed extraction error", async () => {
    vi.mocked(api.createReceipt).mockRejectedValue(new Error("quota_exhausted"))

    const { result } = renderHook(() => useCreateReceipt(), { wrapper })
    result.current.mutate(["page-1"])

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeInstanceOf(Error)
  })
})


function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}
const listKey = ["ai-drafts", "list", { limit: 20 }]
const detailKey = ["ai-receipts", "receipt-1"]
const review = { verified_at: "2026-11-14T00:00:00Z", note: "已查" }
function seed(verified = false) {
  const value = verified ? review : null
  queryClient.setQueryData(listKey, { items: [
    { id: "a", receipt_id: "receipt-1", receipt_review: value },
    { id: "b", receipt_id: "receipt-1", receipt_review: value },
    { id: "c", receipt_id: "other", receipt_review: null },
  ] })
  queryClient.setQueryData(["ai-drafts", "list", { offset: 20 }], { items: [
    { id: "d", receipt_id: "receipt-1", receipt_review: value },
  ] })
  queryClient.setQueryData(detailKey, { receipt_id: "receipt-1", lines: [], review: value })
}
function cachedReviews() {
  return queryClient.getQueryData<DraftListResponse>(listKey)!.items.map((row) => row.receipt_review)
}

describe("收據讀取與核對快取", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.token = "jwt"
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  })
  it("以 token 取得整張收據", async () => {
    const detail: api.ReceiptRead = { receipt_id: "receipt-1", lines: [], review: null }
    vi.mocked(api.getReceipt).mockResolvedValue(detail)
    const { result } = renderHook(() => useReceipt("receipt-1"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.getReceipt).toHaveBeenCalledWith("receipt-1", "jwt")
    expect(result.current.data).toEqual(detail)
  })
  it("未登入不查詢", () => {
    auth.token = null
    renderHook(() => useReceipt("receipt-1"), { wrapper })
    expect(api.getReceipt).not.toHaveBeenCalled()
  })
  it.each([false, true])("標記與取消同步樂觀更新兩份快取：取消=%s", async (cancel) => {
    seed(cancel)
    const gate = deferred<api.ReceiptReview>()
    const deletion = deferred<void>()
    vi.mocked(api.putReceiptReview).mockReturnValue(gate.promise)
    vi.mocked(api.deleteReceiptReview).mockReturnValue(deletion.promise)
    const { result } = renderHook(() => useReceiptReview("receipt-1"), { wrapper })
    act(() => result.current.mutate(cancel ? undefined : "已查"))
    await waitFor(() => expect(cachedReviews()[0]?.note ?? null).toBe(cancel ? null : "已查"))
    expect(cachedReviews()[1]).toEqual(cachedReviews()[0])
    expect(cachedReviews()[2]).toBeNull()
    expect(queryClient.getQueryData<api.ReceiptRead>(detailKey)?.review).toEqual(cachedReviews()[0])
    expect(queryClient.getQueryData<DraftListResponse>(["ai-drafts", "list", { offset: 20 }])!.items[0]!.receipt_review).toEqual(cachedReviews()[0])
    await act(async () => { if (cancel) deletion.resolve(); else gate.resolve(review) })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(cachedReviews()).toEqual([cancel ? null : review, cancel ? null : review, null])
    expect(queryClient.getQueryData<api.ReceiptRead>(detailKey)?.review).toEqual(cancel ? null : review)
  })
  it.each([false, true])("失敗還原核對且保留其他資料變化：取消=%s", async (cancel) => {
    seed(cancel)
    const gate = deferred<api.ReceiptReview>()
    vi.mocked(api.putReceiptReview).mockReturnValue(gate.promise)
    vi.mocked(api.deleteReceiptReview).mockReturnValue(gate.promise as Promise<never>)
    const { result } = renderHook(() => useReceiptReview("receipt-1"), { wrapper })
    act(() => result.current.mutate(cancel ? undefined : "新備註"))
    await waitFor(() => expect(api[cancel ? "deleteReceiptReview" : "putReceiptReview"]).toHaveBeenCalled())
    queryClient.setQueryData<DraftListResponse>(listKey, (current) => ({ ...current!, items: current!.items.map((row) => ({ ...row, status: "accepted" })) }))
    await act(async () => gate.reject(new Error("離線")))
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(cachedReviews()).toEqual([cancel ? review : null, cancel ? review : null, null])
    expect(queryClient.getQueryData<api.ReceiptRead>(detailKey)?.review).toEqual(cancel ? review : null)
    expect(queryClient.getQueryData<DraftListResponse>(listKey)!.items[0]!.status).toBe("accepted")
  })
})
