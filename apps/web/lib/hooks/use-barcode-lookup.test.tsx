import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

const auth = vi.hoisted(() => ({ token: "jwt" as string | null }))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => auth.token,
}))

vi.mock("@/lib/api/barcodes", () => ({
  lookupBarcode: vi.fn(),
}))

import * as api from "@/lib/api/barcodes"
import { useBarcodeLookup } from "./use-barcode-lookup"

let queryClient: QueryClient

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const payload = {
  code: "4710085200016",
  local_matches: [],
  external: {
    source: "openfoodfacts",
    name: "鮮奶",
    description: "瑞穗",
    image_url: null,
    suggested_category_id: null,
  },
  external_status: "ok" as const,
  cached: false,
}

describe("useBarcodeLookup", () => {
  beforeEach(() => {
    auth.token = "jwt"
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
  })

  it("looks up the canonical code with the token", async () => {
    vi.mocked(api.lookupBarcode).mockResolvedValue(payload)

    const { result } = renderHook(() => useBarcodeLookup("4710085200016"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.lookupBarcode).toHaveBeenCalledWith("4710085200016", "jwt")
    expect(result.current.data?.external?.name).toBe("鮮奶")
  })

  it("stays idle when code is null", () => {
    renderHook(() => useBarcodeLookup(null), { wrapper })

    expect(api.lookupBarcode).not.toHaveBeenCalled()
  })

  it("stays idle without a token", () => {
    auth.token = null

    renderHook(() => useBarcodeLookup("4710085200016"), { wrapper })

    expect(api.lookupBarcode).not.toHaveBeenCalled()
  })

  it("does not retry failed lookups", async () => {
    vi.mocked(api.lookupBarcode).mockRejectedValue(new Error("boom"))

    const { result } = renderHook(() => useBarcodeLookup("4710085200016"), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(api.lookupBarcode).toHaveBeenCalledTimes(1)
  })
})
