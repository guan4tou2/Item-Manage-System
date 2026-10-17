import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api/client"
import { useUpdatePreferences } from "./use-preferences"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe("useUpdatePreferences", () => {
  beforeEach(() => {
    auth.token = "jwt"
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
  })

  it("updates the preferences cache and invalidates stats", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      json: async () => ({ theme: "dark", language: "en", currency: "JPY" }),
    } as Response)
    const spy = vi.spyOn(queryClient, "invalidateQueries")

    const { result } = renderHook(() => useUpdatePreferences(), { wrapper })
    result.current.mutate({ currency: "JPY" })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(apiFetch).toHaveBeenCalledWith(
      "/users/me/preferences",
      expect.objectContaining({ method: "PUT" }),
    )
    expect(queryClient.getQueryData(["preferences", "me"])).toEqual({
      theme: "dark",
      language: "en",
      currency: "JPY",
    })
    const keys = spy.mock.calls.map((call) =>
      JSON.stringify(
        (call[0] as { queryKey?: readonly unknown[] } | undefined)?.queryKey,
      ),
    )
    expect(keys).toContain(JSON.stringify(["stats"]))
  })
})
