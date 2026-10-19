import { afterEach, describe, expect, it, vi } from "vitest"

import {
  acceptDraft,
  activeDraftTotal,
  createDrafts,
  discardDraft,
  discardDrafts,
  listDrafts,
  processDraft,
  suggestClassification,
} from "./ai-drafts"
import type { DraftListResponse, DraftRead } from "./ai-drafts"

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

const draft: DraftRead = {
  id: "draft-1",
  source: "batch_photo",
  status: "pending",
  image_id: "img-1",
  item_id: null,
  error_code: null,
  payload: {
    version: 1,
    ai: null,
    history: { category: null, location: null, tags: [] },
  },
  processed_at: null,
  created_at: "2026-10-19T02:11:03Z",
}

const list: DraftListResponse = {
  items: [draft],
  total: 1,
  counts: { pending: 1, processing: 0, ready: 0, failed: 0, accepted: 0, discarded: 0 },
}

function requestOf(fetchMock: ReturnType<typeof mockFetch>, index = 0) {
  const init = fetchMock.mock.calls[index]?.[1] as RequestInit | undefined
  return {
    url: String(fetchMock.mock.calls[index]?.[0]),
    method: init?.method,
    body: typeof init?.body === "string" ? JSON.parse(init.body) : null,
  }
}

describe("ai-drafts api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("creates drafts from image ids", async () => {
    const fetchMock = mockFetch(
      { created: [draft], skipped_image_ids: ["img-9"] },
      201,
    )

    const result = await createDrafts(["img-1", "img-9"], "jwt")

    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/drafts",
      method: "POST",
      body: { image_ids: ["img-1", "img-9"] },
    })
    expect(result.created[0]?.id).toBe("draft-1")
    expect(result.skipped_image_ids).toEqual(["img-9"])
  })

  it("lists drafts without a query string when no params are given", async () => {
    const fetchMock = mockFetch(list)

    const result = await listDrafts({}, "jwt")

    expect(requestOf(fetchMock)).toMatchObject({ url: "/api/ai/drafts" })
    expect(result.counts.pending).toBe(1)
  })

  it("lists drafts with status and paging params", async () => {
    const fetchMock = mockFetch(list)

    await listDrafts({ status: "ready", limit: 5, offset: 10 }, "jwt")

    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/drafts?status=ready&limit=5&offset=10",
      method: undefined,
    })
  })

  it("processes a draft", async () => {
    const fetchMock = mockFetch({ ...draft, status: "ready" })

    const result = await processDraft("draft-1", "jwt")

    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/drafts/draft-1/process",
      method: "POST",
    })
    expect(result.status).toBe("ready")
  })

  it("accepts a draft with edited fields", async () => {
    const fetchMock = mockFetch({
      draft: { ...draft, status: "accepted", item_id: "item-1" },
      item: { id: "item-1", name: "咖啡濾杯" },
    })

    const result = await acceptDraft(
      "draft-1",
      { name: "咖啡濾杯", category_id: 3, quantity: 2, tag_names: ["咖啡"] },
      "jwt",
    )

    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/drafts/draft-1/accept",
      method: "POST",
      body: { name: "咖啡濾杯", category_id: 3, quantity: 2, tag_names: ["咖啡"] },
    })
    expect(result.item?.name).toBe("咖啡濾杯")
    expect(result.draft.item_id).toBe("item-1")
  })

  it("discards a single draft", async () => {
    const fetchMock = mockFetch({ ...draft, status: "discarded" })

    const result = await discardDraft("draft-1", "jwt")

    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/drafts/draft-1/discard",
      method: "POST",
    })
    expect(result.status).toBe("discarded")
  })

  it("discards many drafts in one request", async () => {
    const fetchMock = mockFetch({
      discarded: 1,
      skipped: [{ id: "draft-2", reason: "already discarded" }],
    })

    const result = await discardDrafts(["draft-1", "draft-2"], "jwt")

    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/drafts/discard",
      method: "POST",
      body: { ids: ["draft-1", "draft-2"] },
    })
    expect(result.discarded).toBe(1)
    expect(result.skipped[0]?.reason).toBe("already discarded")
  })

  it("suggests classification from the user's history", async () => {
    const fetchMock = mockFetch({
      category: { id: 3, name: "廚房用品", item_count: 12, score: 4 },
      location: null,
      tags: [{ name: "咖啡", item_count: 6, score: 3 }],
    })

    const result = await suggestClassification("陶瓷咖啡杯", "jwt")

    expect(requestOf(fetchMock)).toMatchObject({
      url: "/api/ai/suggest-classification",
      method: "POST",
      body: { name: "陶瓷咖啡杯" },
    })
    expect(result.category?.name).toBe("廚房用品")
    expect(result.tags[0]?.name).toBe("咖啡")
  })

  it("throws an ApiError on non-2xx responses", async () => {
    mockFetch({ detail: "draft already accepted" }, 409)

    await expect(processDraft("draft-1", "jwt")).rejects.toMatchObject({ status: 409 })
  })

  it("counts only active statuses for the queue badge", () => {
    expect(
      activeDraftTotal({ pending: 1, processing: 2, ready: 3, failed: 4, accepted: 9, discarded: 9 }),
    ).toBe(10)
    expect(
      activeDraftTotal({ pending: 0, processing: 0, ready: 0, failed: 0, accepted: 1, discarded: 1 }),
    ).toBe(0)
  })
})
