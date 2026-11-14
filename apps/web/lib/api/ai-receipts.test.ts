import { afterEach, describe, expect, it, vi } from "vitest"

import { createReceipt, getReceipt, putReceiptReview, deleteReceiptReview } from "./ai-receipts"
import type { ReceiptCreateResponse } from "./ai-receipts"

const originalFetch = global.fetch

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  })
}

function mockFetch(data: unknown, status = 200) {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL, _init?: RequestInit) => jsonResponse(data, status),
  )
  global.fetch = fetchMock as unknown as typeof global.fetch
  return fetchMock
}

function requestOf(fetchMock: ReturnType<typeof mockFetch>, index = 0) {
  const init = fetchMock.mock.calls[index]?.[1] as RequestInit | undefined
  return {
    url: String(fetchMock.mock.calls[index]?.[0]),
    method: init?.method,
    body: typeof init?.body === "string" ? JSON.parse(init.body) : null,
  }
}

const response: ReceiptCreateResponse = {
  receipt_id: "receipt-1",
  truncated: false,
  created: [],
}

describe("ai-receipts api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("creates a receipt from page image ids", async () => {
    const fetchMock = mockFetch(response, 201)

    const result = await createReceipt(["page-1", "page-2"], "jwt")

    expect(result).toEqual(response)
    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/receipts",
      method: "POST",
      body: { image_ids: ["page-1", "page-2"] },
    })
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    const headers = new Headers(init.headers)
    expect(headers.get("authorization")).toBe("Bearer jwt")
  })

  it("surfaces the error code from a failed extraction", async () => {
    mockFetch({ detail: "quota_exhausted" }, 429)

    await expect(createReceipt(["page-1"], "jwt")).rejects.toMatchObject({
      status: 429,
      body: { detail: "quota_exhausted" },
    })
  })

  it("works without a token (viewer guard rejects server-side)", async () => {
    const fetchMock = mockFetch({ detail: "ai_disabled" }, 503)

    await expect(createReceipt(["page-1"], null)).rejects.toMatchObject({
      status: 503,
    })
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(init.headers).get("authorization")).toBeNull()
  })

  it("讀取整張收據並送出認證", async () => {
    const detail = { receipt_id: "r1", lines: [], review: null }
    const fetchMock = mockFetch(detail)
    expect(await getReceipt("r1", "jwt")).toEqual(detail)
    expect(requestOf(fetchMock).url).toBe("/api/ai/receipts/r1")
    expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).get("authorization")).toBe("Bearer jwt")
  })

  it("送出核對備註並回傳核對紀錄", async () => {
    const review = { verified_at: "2026-11-14T00:00:00Z", note: "已查" }
    const fetchMock = mockFetch(review)
    expect(await putReceiptReview("r1", "已查", "jwt")).toEqual(review)
    expect(requestOf(fetchMock)).toEqual({ url: "/api/ai/receipts/r1/review", method: "PUT", body: { note: "已查" } })
  })

  it("取消核對接受沒有 JSON body 的 204", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }))
    global.fetch = fetchMock
    await expect(deleteReceiptReview("r1", "jwt")).resolves.toBeUndefined()
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/ai/receipts/r1/review")
    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe("DELETE")
  })

})
