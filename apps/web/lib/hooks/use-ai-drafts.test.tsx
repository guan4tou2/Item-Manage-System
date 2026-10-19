import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/ai-drafts", () => ({
  listDrafts: vi.fn(),
  createDrafts: vi.fn(),
  processDraft: vi.fn(),
  acceptDraft: vi.fn(),
  discardDraft: vi.fn(),
  discardDrafts: vi.fn(),
  suggestClassification: vi.fn(),
}))

import * as api from "@/lib/api/ai-drafts"
import type { DraftAcceptResponse, DraftListResponse, DraftRead } from "@/lib/api/ai-drafts"
import {
  useAcceptDraft,
  useDiscardDraft,
  useDiscardDrafts,
  useDraftCounts,
  useDrafts,
  useProcessDraft,
} from "./use-ai-drafts"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const draft: DraftRead = {
  id: "draft-1",
  source: "batch_photo",
  status: "ready",
  image_id: "img-1",
  item_id: null,
  error_code: null,
  payload: {
    version: 1,
    ai: {
      name: "咖啡濾杯",
      description: "陶瓷手沖濾杯",
      category_suggestion: "廚房用品",
      tag_suggestions: ["咖啡"],
    },
    history: {
      category: { id: 3, name: "廚房用品", item_count: 12, score: 4 },
      location: { id: 7, name: "廚房", item_count: 9, score: 3 },
      tags: [{ name: "咖啡", item_count: 6, score: 3 }],
    },
  },
  processed_at: "2026-10-19T02:11:09Z",
  created_at: "2026-10-19T02:11:03Z",
}

const list: DraftListResponse = {
  items: [draft],
  total: 1,
  counts: { pending: 0, processing: 0, ready: 1, failed: 2, accepted: 4, discarded: 1 },
}

describe("use-ai-drafts", () => {
  beforeEach(() => {
    auth.token = "jwt"
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
  })

  it("lists drafts with the access token and default paging", async () => {
    vi.mocked(api.listDrafts).mockResolvedValue(list)

    const { result } = renderHook(() => useDrafts(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.listDrafts).toHaveBeenCalledWith(
      { status: undefined, limit: 20, offset: 0 },
      "jwt",
    )
    expect(result.current.data).toEqual(list)
  })

  it("lists drafts filtered by status", async () => {
    vi.mocked(api.listDrafts).mockResolvedValue(list)

    const { result } = renderHook(() => useDrafts({ status: "failed", limit: 5 }), {
      wrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.listDrafts).toHaveBeenCalledWith(
      { status: "failed", limit: 5, offset: 0 },
      "jwt",
    )
  })

  it("does not list drafts without a token", () => {
    auth.token = null

    renderHook(() => useDrafts(), { wrapper })

    expect(api.listDrafts).not.toHaveBeenCalled()
  })

  it("exposes full draft counts with a single-row list request", async () => {
    vi.mocked(api.listDrafts).mockResolvedValue(list)

    const { result } = renderHook(() => useDraftCounts(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.listDrafts).toHaveBeenCalledWith({ limit: 1, offset: 0 }, "jwt")
    expect(result.current.data).toEqual(list.counts)
  })

  it("processes a draft and invalidates the drafts cache", async () => {
    vi.mocked(api.processDraft).mockResolvedValue(draft)
    const spy = vi.spyOn(queryClient, "invalidateQueries")

    const { result } = renderHook(() => useProcessDraft(), { wrapper })
    result.current.mutate("draft-1")

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.processDraft).toHaveBeenCalledWith("draft-1", "jwt")
    expect(spy.mock.calls.map((call) => call[0]?.queryKey)).toContainEqual(["ai-drafts"])
  })

  it("accepts a draft and invalidates drafts and items caches", async () => {
    vi.mocked(api.acceptDraft).mockResolvedValue({
      draft: { ...draft, status: "accepted", item_id: "item-1" },
      item: { id: "item-1", name: "咖啡濾杯" } as DraftAcceptResponse["item"],
    })
    const spy = vi.spyOn(queryClient, "invalidateQueries")

    const { result } = renderHook(() => useAcceptDraft(), { wrapper })
    result.current.mutate({ id: "draft-1", body: { name: "咖啡濾杯", quantity: 1 } })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.acceptDraft).toHaveBeenCalledWith(
      "draft-1",
      { name: "咖啡濾杯", quantity: 1 },
      "jwt",
    )
    const keys = spy.mock.calls.map((call) => call[0]?.queryKey)
    expect(keys).toContainEqual(["ai-drafts"])
    expect(keys).toContainEqual(["items"])
  })

  it("discards a single draft", async () => {
    vi.mocked(api.discardDraft).mockResolvedValue({ ...draft, status: "discarded" })

    const { result } = renderHook(() => useDiscardDraft(), { wrapper })
    result.current.mutate("draft-1")

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.discardDraft).toHaveBeenCalledWith("draft-1", "jwt")
  })

  it("bulk discards drafts and invalidates the drafts cache", async () => {
    vi.mocked(api.discardDrafts).mockResolvedValue({ discarded: 2, skipped: [] })
    const spy = vi.spyOn(queryClient, "invalidateQueries")

    const { result } = renderHook(() => useDiscardDrafts(), { wrapper })
    result.current.mutate(["draft-1", "draft-2"])

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.discardDrafts).toHaveBeenCalledWith(["draft-1", "draft-2"], "jwt")
    expect(spy.mock.calls.map((call) => call[0]?.queryKey)).toContainEqual(["ai-drafts"])
  })
})
