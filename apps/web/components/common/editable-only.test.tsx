import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"

import { EditableOnly } from "./editable-only"

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

describe("EditableOnly", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: "jwt", user: user(true) })
  })

  it("renders nothing for a read-only viewer", () => {
    render(
      <EditableOnly>
        <button>edit</button>
      </EditableOnly>,
    )
    expect(screen.queryByRole("button", { name: "edit" })).not.toBeInTheDocument()
  })

  it("renders children for writers", () => {
    useAuthStore.setState({ accessToken: "jwt", user: user(false) })
    render(
      <EditableOnly>
        <button>edit</button>
      </EditableOnly>,
    )
    expect(screen.getByRole("button", { name: "edit" })).toBeInTheDocument()
  })
})
