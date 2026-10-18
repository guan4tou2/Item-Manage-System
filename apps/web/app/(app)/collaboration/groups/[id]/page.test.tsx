import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import GroupDetailPage from "./page"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "g1" }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

const hooks = vi.hoisted(() => ({
  group: vi.fn(),
  remove: vi.fn(),
  del: vi.fn(),
  add: vi.fn(),
  updateRole: vi.fn(),
}))

vi.mock("@/lib/hooks/use-groups", () => ({
  useGroup: () => hooks.group(),
  useRemoveGroupMember: () => hooks.remove(),
  useDeleteGroup: () => hooks.del(),
  useAddGroupMember: () => hooks.add(),
  useUpdateMemberRole: () => hooks.updateRole(),
}))

const toastSuccess = vi.hoisted(() => vi.fn())
const toastError = vi.hoisted(() => vi.fn())
vi.mock("sonner", () => ({
  toast: {
    success: (message: string) => toastSuccess(message),
    error: (message: string) => toastError(message),
  },
}))

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

type Role = "owner" | "admin" | "editor" | "viewer"

function group(myRole: Role, isOwner: boolean) {
  return {
    id: "g1",
    name: "Home",
    owner_id: "owner-1",
    owner_username: "olivia",
    is_owner: isOwner,
    member_count: 4,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    my_role: myRole,
    members: [
      { user_id: "owner-1", username: "olivia", joined_at: "2026-01-01T00:00:00Z", role: "owner" },
      { user_id: "admin-1", username: "alice", joined_at: "2026-01-01T00:00:00Z", role: "admin" },
      { user_id: "editor-1", username: "bob", joined_at: "2026-01-01T00:00:00Z", role: "editor" },
      { user_id: "viewer-1", username: "carol", joined_at: "2026-01-01T00:00:00Z", role: "viewer" },
    ],
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <GroupDetailPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("GroupDetailPage role management (Phase 30)", () => {
  beforeEach(() => {
    hooks.remove.mockReturnValue({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false })
    hooks.del.mockReturnValue({ mutateAsync: vi.fn(), isPending: false })
    hooks.add.mockReturnValue({ mutateAsync: vi.fn(), isPending: false })
    hooks.updateRole.mockReturnValue({ mutate: vi.fn(), isPending: false })
  })

  it("lets the owner change member roles but never the owner row", () => {
    hooks.group.mockReturnValue({ data: group("owner", true), isLoading: false })
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "owner-1", is_read_only: false } as never,
    })
    renderPage()

    expect(screen.getByRole("combobox", { name: "Role for alice" })).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Role for bob" })).toBeInTheDocument()
    expect(screen.getByRole("combobox", { name: "Role for carol" })).toBeInTheDocument()
    expect(screen.queryByRole("combobox", { name: "Role for olivia" })).not.toBeInTheDocument()
    expect(screen.getByText("Owner")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Add member" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete group" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Leave group" })).not.toBeInTheDocument()
  })

  it("lets an admin manage roles without owner-only actions", () => {
    hooks.group.mockReturnValue({ data: group("admin", false), isLoading: false })
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "admin-1", is_read_only: false } as never,
    })
    renderPage()

    expect(screen.getByRole("combobox", { name: "Role for bob" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Add member" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Delete group" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Leave group" })).toBeInTheDocument()
  })

  it.each([
    ["editor" as const],
    ["viewer" as const],
  ])("renders member roles as read-only badges for %s", (myRole) => {
    hooks.group.mockReturnValue({ data: group(myRole, false), isLoading: false })
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "editor-1", is_read_only: false } as never,
    })
    renderPage()

    expect(screen.queryAllByRole("combobox")).toHaveLength(0)
    expect(screen.getByText("Admin")).toBeInTheDocument()
    expect(screen.getByText("Editor")).toBeInTheDocument()
    expect(screen.getByText("Viewer")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Add member" })).not.toBeInTheDocument()
    expect(screen.queryAllByRole("button", { name: "Remove" })).toHaveLength(0)
    expect(screen.getByRole("button", { name: "Leave group" })).toBeInTheDocument()
  })

  it("changes a member role through PATCH and reports the result", async () => {
    const mutate = vi.fn()
    hooks.updateRole.mockReturnValue({ mutate, isPending: false })
    hooks.group.mockReturnValue({ data: group("owner", true), isLoading: false })
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "owner-1", is_read_only: false } as never,
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole("combobox", { name: "Role for carol" }))
    await user.click(await screen.findByRole("option", { name: "Admin" }))

    expect(mutate).toHaveBeenCalledTimes(1)
    const [variables, options] = mutate.mock.calls[0] as [
      { userId: string; role: string },
      { onSuccess: () => void; onError: () => void },
    ]
    expect(variables).toEqual({ userId: "viewer-1", role: "admin" })
    options.onSuccess()
    expect(toastSuccess).toHaveBeenCalled()
  })

  it("reports a failed role change", async () => {
    const mutate = vi.fn()
    hooks.updateRole.mockReturnValue({ mutate, isPending: false })
    hooks.group.mockReturnValue({ data: group("owner", true), isLoading: false })
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "owner-1", is_read_only: false } as never,
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole("combobox", { name: "Role for bob" }))
    await user.click(await screen.findByRole("option", { name: "Viewer" }))

    const options = mutate.mock.calls[0]?.[1] as { onError: () => void } | undefined
    options?.onError()
    expect(toastError).toHaveBeenCalled()
  })
})
