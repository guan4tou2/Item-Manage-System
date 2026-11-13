import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"

vi.mock("@/lib/api/profile", () => ({
  getMe: vi.fn(),
  updateProfile: vi.fn(),
  changePassword: vi.fn(),
  bootstrapAdmin: vi.fn(),
}))

import * as api from "@/lib/api/profile"
import { useChangePassword } from "./use-profile"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useChangePassword", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ accessToken: "old-jwt", user: null })
  })

  it("writes the re-issued access token back to the auth store", async () => {
    vi.mocked(api.changePassword).mockResolvedValue({ success: true, access_token: "new-jwt", token_type: "bearer" })
    const { result } = renderHook(() => useChangePassword(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({ current_password: "a", new_password: "bbbbbbbb" })
    })

    expect(api.changePassword).toHaveBeenCalledWith({ current_password: "a", new_password: "bbbbbbbb" }, "old-jwt")
    await waitFor(() => expect(useAuthStore.getState().accessToken).toBe("new-jwt"))
  })

  it("keeps the old token when the change fails", async () => {
    vi.mocked(api.changePassword).mockRejectedValue(new Error("400"))
    const { result } = renderHook(() => useChangePassword(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({ current_password: "a", new_password: "bbbbbbbb" }).catch(() => undefined)
    })

    expect(useAuthStore.getState().accessToken).toBe("old-jwt")
  })
})
