import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/batches", () => ({
  listBatches: vi.fn(),
  createBatch: vi.fn(),
  updateBatch: vi.fn(),
  deleteBatch: vi.fn(),
  consumeBatch: vi.fn(),
  consumeFefo: vi.fn(),
  disableBatches: vi.fn(),
}))

import * as api from "@/lib/api/batches"
import { useBatches, useConsumeBatch, useConsumeFefo, useCreateBatch } from "./use-batches"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe("use-batches", () => {
  beforeEach(() => {
    auth.token = "jwt"
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
  })

  it("fetches batches for the item with the access token", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([{ id: "batch-1", quantity: 2 }] as never)

    const { result } = renderHook(() => useBatches("item-1"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.listBatches).toHaveBeenCalledWith("item-1", "jwt")
    expect(result.current.data).toEqual([{ id: "batch-1", quantity: 2 }])
  })

  it("does not fetch without a token", () => {
    auth.token = null

    renderHook(() => useBatches("item-1"), { wrapper })

    expect(api.listBatches).not.toHaveBeenCalled()
  })

  it("invalidates batches, items, and stats after FEFO consume", async () => {
    vi.mocked(api.consumeFefo).mockResolvedValue({
      consumed: [{ batch_id: "batch-1", quantity: 1 }],
    } as never)
    const spy = vi.spyOn(queryClient, "invalidateQueries")

    const { result } = renderHook(() => useConsumeFefo(), { wrapper })
    result.current.mutate({ itemId: "item-1", quantity: 1 })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.consumeFefo).toHaveBeenCalledWith("item-1", { quantity: 1 }, "jwt")
    const keys = spy.mock.calls.map((call) =>
      JSON.stringify((call[0] as { queryKey?: readonly unknown[] } | undefined)?.queryKey),
    )
    expect(keys).toContain(JSON.stringify(["batches"]))
    expect(keys).toContain(JSON.stringify(["items"]))
    expect(keys).toContain(JSON.stringify(["stats"]))
  })

  it("creates a batch through the create hook", async () => {
    vi.mocked(api.createBatch).mockResolvedValue({ id: "batch-2" } as never)

    const { result } = renderHook(() => useCreateBatch("item-1"), { wrapper })
    result.current.mutate({ quantity: 3 })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.createBatch).toHaveBeenCalledWith("item-1", { quantity: 3 }, "jwt")
  })

  it("optimistically decrements batch and item caches while in flight", async () => {
    queryClient.setQueryData(["batches", "item-1"], [
      { id: "batch-1", quantity: 3, is_depleted: false },
    ])
    queryClient.setQueryData(["items", "item-1"], { id: "item-1", quantity: 3 })
    vi.mocked(api.consumeBatch).mockImplementation(() => new Promise<never>(() => {}))

    const { result } = renderHook(() => useConsumeBatch("item-1"), { wrapper })
    result.current.mutate({ batchId: "batch-1", quantity: 1 })

    await waitFor(() => {
      const rows = queryClient.getQueryData<{ quantity: number }[]>(["batches", "item-1"])
      expect(rows?.[0]?.quantity).toBe(2)
    })
    expect(
      queryClient.getQueryData<{ quantity: number }>(["items", "item-1"])?.quantity,
    ).toBe(2)
  })

  it("rolls back optimistic caches on consume error", async () => {
    const originalBatches = [{ id: "batch-1", quantity: 3, is_depleted: false }]
    queryClient.setQueryData(["batches", "item-1"], originalBatches)
    queryClient.setQueryData(["items", "item-1"], { id: "item-1", quantity: 3 })
    vi.mocked(api.consumeBatch).mockRejectedValue(new Error("boom"))

    const { result } = renderHook(() => useConsumeBatch("item-1"), { wrapper })
    result.current.mutate({ batchId: "batch-1", quantity: 1 })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(queryClient.getQueryData(["batches", "item-1"])).toEqual(originalBatches)
    expect(
      queryClient.getQueryData<{ quantity: number }>(["items", "item-1"])?.quantity,
    ).toBe(3)
  })

  it("optimistically decrements matching list rows for FEFO consume", async () => {
    queryClient.setQueryData(["items", { q: "milk" }], {
      items: [
        { id: "item-1", quantity: 2 },
        { id: "item-2", quantity: 5 },
      ],
      total: 2,
      page: 1,
      per_page: 20,
    })
    vi.mocked(api.consumeFefo).mockImplementation(() => new Promise<never>(() => {}))

    const { result } = renderHook(() => useConsumeFefo(), { wrapper })
    result.current.mutate({ itemId: "item-1" })

    await waitFor(() => {
      const data = queryClient.getQueryData<{ items: { id: string; quantity: number }[] }>([
        "items",
        { q: "milk" },
      ])
      expect(data?.items[0]?.quantity).toBe(1)
    })
    const data = queryClient.getQueryData<{ items: { id: string; quantity: number }[] }>([
      "items",
      { q: "milk" },
    ])
    expect(data?.items[1]?.quantity).toBe(5)
    expect(api.consumeFefo).toHaveBeenCalledWith("item-1", { quantity: 1 }, "jwt")
  })

  it("rolls back list rows when FEFO consume fails", async () => {
    const original = {
      items: [{ id: "item-1", quantity: 2 }],
      total: 1,
      page: 1,
      per_page: 20,
    }
    queryClient.setQueryData(["items", { q: "milk" }], original)
    vi.mocked(api.consumeFefo).mockRejectedValue(new Error("boom"))

    const { result } = renderHook(() => useConsumeFefo(), { wrapper })
    result.current.mutate({ itemId: "item-1" })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(queryClient.getQueryData(["items", { q: "milk" }])).toEqual(original)
  })
})
