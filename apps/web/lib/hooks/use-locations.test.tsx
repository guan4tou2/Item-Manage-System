import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/locations", () => ({
  listLocations: vi.fn(),
  getLocationTree: vi.fn(),
  createLocation: vi.fn(),
  updateLocation: vi.fn(),
  moveLocation: vi.fn(),
  reorderLocations: vi.fn(),
  deleteLocation: vi.fn(),
}))

import * as api from "@/lib/api/locations"
import { useDeleteLocation, useLocationTree, useLocations, useMoveLocation } from "./use-locations"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe("use-locations", () => {
  beforeEach(() => {
    auth.token = "jwt"
    vi.clearAllMocks()
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  })

  it("fetches the flat list with the access token", async () => {
    vi.mocked(api.listLocations).mockResolvedValue([])

    const { result } = renderHook(() => useLocations(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.listLocations).toHaveBeenCalledWith("jwt")
  })

  it("fetches the nested tree", async () => {
    vi.mocked(api.getLocationTree).mockResolvedValue([])

    const { result } = renderHook(() => useLocationTree(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.getLocationTree).toHaveBeenCalledWith("jwt")
  })

  it("does not fetch without a token", () => {
    auth.token = null
    renderHook(() => useLocations(), { wrapper })
    expect(api.listLocations).not.toHaveBeenCalled()
  })

  it("moves a node and invalidates locations, items, and stats", async () => {
    vi.mocked(api.moveLocation).mockResolvedValue({} as never)
    const invalidate = vi.spyOn(queryClient, "invalidateQueries")

    const { result } = renderHook(() => useMoveLocation(), { wrapper })
    result.current.mutate({ id: 7, parentId: 3 })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.moveLocation).toHaveBeenCalledWith(7, 3, "jwt")
    const keys = invalidate.mock.calls.map((call) => JSON.stringify(call[0]?.queryKey))
    expect(keys).toContain(JSON.stringify(["locations"]))
    expect(keys).toContain(JSON.stringify(["items"]))
    expect(keys).toContain(JSON.stringify(["stats"]))
  })

  it("surfaces the 409 delete error to callers", async () => {
    const error = Object.assign(new Error("api error 409"), {
      status: 409,
      body: { detail: { code: "has_children", items: 0, children: 2 } },
    })
    vi.mocked(api.deleteLocation).mockRejectedValue(error)

    const { result } = renderHook(() => useDeleteLocation(), { wrapper })
    result.current.mutate(5)

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect((result.current.error as unknown as { status: number }).status).toBe(409)
  })
})
