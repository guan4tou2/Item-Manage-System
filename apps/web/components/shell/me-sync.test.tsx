import { render, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"

import { MeSync } from "./me-sync"

const meState: { value: { data: unknown } } = { value: { data: undefined } }

vi.mock("@/lib/hooks/use-profile", () => ({
  useMe: () => meState.value,
}))

function user(isReadOnly: boolean) {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    email: "v@t.io",
    username: "viewer",
    is_active: true,
    is_admin: false,
    created_at: "2026-01-01T00:00:00Z",
    is_read_only: isReadOnly,
  } as never
}

describe("MeSync", () => {
  beforeEach(() => {
    meState.value = { data: undefined }
    useAuthStore.setState({ accessToken: "jwt", user: user(false) })
  })

  it("syncs /users/me result into the auth store (role downgraded mid-session)", async () => {
    meState.value = { data: user(true) }
    render(<MeSync />)
    await waitFor(() =>
      expect(useAuthStore.getState().user?.is_read_only).toBe(true),
    )
    expect(useAuthStore.getState().accessToken).toBe("jwt")
  })

  it("does nothing while logged out", async () => {
    meState.value = { data: user(true) }
    useAuthStore.setState({ accessToken: null, user: null })
    render(<MeSync />)
    await Promise.resolve()
    expect(useAuthStore.getState().user).toBeNull()
  })
})
