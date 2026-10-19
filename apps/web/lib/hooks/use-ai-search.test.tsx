import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/ai-search", () => ({
  aiSearch: vi.fn(),
  askItems: vi.fn(),
}))

import * as api from "@/lib/api/ai-search"
import type { AskResponse, SearchResponse } from "@/lib/api/ai-search"
import { useAiAsk, useAiSearch } from "./use-ai-search"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const searchResponse = {
  filters: { q: "藥" },
  applied: {
    q: "藥",
    category: null,
    location: null,
    tags: [],
    expiry: null,
    loan: null,
    favorite: null,
    min_quantity: null,
    max_quantity: null,
    sort: null,
  },
  unresolved: [],
  items: [],
  total: 0,
  fallback_reason: "ai_disabled",
} as SearchResponse

const askResponse = {
  answer: "資料不足。",
  citations: [],
  grounded: false,
} as AskResponse

describe("useAiSearch / useAiAsk", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.token = "jwt"
    queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    })
  })

  it("searches with the access token", async () => {
    vi.mocked(api.aiSearch).mockResolvedValue(searchResponse)

    const { result } = renderHook(() => useAiSearch(), { wrapper })
    result.current.mutate("廚房裡快過期的藥")

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.aiSearch).toHaveBeenCalledWith("廚房裡快過期的藥", "jwt")
    expect(result.current.data?.fallback_reason).toBe("ai_disabled")
  })

  it("exposes search failures (e.g. opt-in required)", async () => {
    vi.mocked(api.aiSearch).mockRejectedValue(new Error("ai_opt_in_required"))

    const { result } = renderHook(() => useAiSearch(), { wrapper })
    result.current.mutate("藥")

    await waitFor(() => expect(result.current.isError).toBe(true))
  })

  it("asks with the current item ids", async () => {
    vi.mocked(api.askItems).mockResolvedValue(askResponse)

    const { result } = renderHook(() => useAiAsk(), { wrapper })
    result.current.mutate({ question: "有哪些快過期？", itemIds: ["item-1"] })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.askItems).toHaveBeenCalledWith("有哪些快過期？", ["item-1"], "jwt")
  })

  it("resets the previous answer when asking again", async () => {
    vi.mocked(api.askItems).mockResolvedValue(askResponse)

    const { result } = renderHook(() => useAiAsk(), { wrapper })
    result.current.mutate({ question: "第一題", itemIds: [] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    vi.mocked(api.askItems).mockResolvedValue({ ...askResponse, answer: "第二題答案" })
    result.current.mutate({ question: "第二題", itemIds: [] })

    await waitFor(() => expect(result.current.data?.answer).toBe("第二題答案"))
  })
})
