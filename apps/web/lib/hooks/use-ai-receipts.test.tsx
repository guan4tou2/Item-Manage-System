import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/ai-receipts", () => ({
  createReceipt: vi.fn(),
}))

import * as api from "@/lib/api/ai-receipts"
import { useCreateReceipt } from "./use-ai-receipts"

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
