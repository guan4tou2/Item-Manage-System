import { afterEach, describe, expect, it, vi } from "vitest"

import { askItems, aiSearch } from "./ai-search"
import type { AskResponse, SearchResponse } from "./ai-search"

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

const searchResponse: SearchResponse = {
  filters: {
    q: "藥",
    category_id: null,
    location_id: null,
    tag_ids: [],
    expiry: "expiring_soon",
    loan: null,
    favorite: null,
    min_quantity: null,
    max_quantity: null,
    sort: null,
  },
  applied: {
    q: "藥",
    category: null,
    location: { id: 7, name: "廚房", path: "1F / 廚房" },
    tags: [],
    expiry: "expiring_soon",
    loan: null,
    favorite: null,
    min_quantity: null,
    max_quantity: null,
    sort: "expiry_asc",
  },
  unresolved: [],
  items: [],
  total: 0,
  fallback_reason: null,
}

const askResponse: AskResponse = {
  answer: "有 1 件[#1]。",
  citations: [{ item_id: "item-1", name: "感冒藥", path: "1F / 廚房" }],
  grounded: true,
}

describe("ai-search api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("posts the natural language query", async () => {
    const fetchMock = mockFetch(searchResponse)

    const result = await aiSearch("廚房裡快過期的藥", "jwt")

    expect(result).toEqual(searchResponse)
    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/search",
      method: "POST",
      body: { query: "廚房裡快過期的藥" },
    })
    expect(new Headers(fetchMock.mock.calls[0]?.[1]?.headers).get("authorization")).toBe(
      "Bearer jwt",
    )
  })

  it("surfaces the opt-in error code", async () => {
    mockFetch({ detail: "ai_opt_in_required" }, 403)

    await expect(aiSearch("藥", "jwt")).rejects.toMatchObject({
      status: 403,
      body: { detail: "ai_opt_in_required" },
    })
  })

  it("posts the question and item ids", async () => {
    const fetchMock = mockFetch(askResponse)

    const result = await askItems("有哪些快過期？", ["item-1"], "jwt")

    expect(result).toEqual(askResponse)
    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/ask",
      method: "POST",
      body: { question: "有哪些快過期？", item_ids: ["item-1"] },
    })
  })

  it("posts an empty item_ids list when no selection", async () => {
    const fetchMock = mockFetch(askResponse)

    await askItems("有哪些快過期？", [], "jwt")

    expect(requestOf(fetchMock).body).toEqual({
      question: "有哪些快過期？",
      item_ids: [],
    })
  })

  it("surfaces ask error codes", async () => {
    mockFetch({ detail: "quota_exhausted" }, 429)

    await expect(askItems("x", [], "jwt")).rejects.toMatchObject({
      status: 429,
      body: { detail: "quota_exhausted" },
    })
  })
})
