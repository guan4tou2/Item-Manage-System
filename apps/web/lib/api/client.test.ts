import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useAuthStore } from "@/lib/auth/auth-store"
import { ApiError, apiFetch } from "./client"

const originalFetch = global.fetch

describe("apiFetch 401 handling", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: "jwt", user: null })
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("clears the auth store on 401", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "unauthorized" }), { status: 401 }),
    )
    await expect(apiFetch("/anything")).rejects.toBeInstanceOf(ApiError)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("does not clear the store on non-401 errors", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "boom" }), { status: 500 }),
    )
    await expect(apiFetch("/anything")).rejects.toBeInstanceOf(ApiError)
    expect(useAuthStore.getState().accessToken).toBe("jwt")
  })
})
