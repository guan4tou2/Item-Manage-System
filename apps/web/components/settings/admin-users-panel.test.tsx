import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { AdminUsersPanel } from "./admin-users-panel"

const mocks = vi.hoisted(() => ({
  sendTestMutateAsync: vi.fn(),
  setActiveMutateAsync: vi.fn(),
  rows: [
    { id: "u1", username: "admin", email: "admin@example.com", is_active: true, is_admin: true },
    { id: "u2", username: "member", email: "member@example.com", is_active: true, is_admin: false },
  ],
}))

vi.mock("@/lib/hooks/use-admin", () => ({
  useAdminUsers: () => ({ data: mocks.rows, isLoading: false }),
  useSetUserActive: () => ({ mutateAsync: mocks.setActiveMutateAsync, isPending: false }),
  useSendTestNotification: () => ({ mutateAsync: mocks.sendTestMutateAsync, isPending: false }),
}))

vi.mock("@/lib/auth/auth-store", () => ({
  useAuthStore: (selector: (state: { user: { id: string } }) => unknown) =>
    selector({ user: { id: "u1" } }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.admin

function renderPanel() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <AdminUsersPanel />
    </NextIntlClientProvider>,
  )
}

describe("AdminUsersPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.setActiveMutateAsync.mockResolvedValue(undefined)
    mocks.sendTestMutateAsync.mockResolvedValue(undefined)
  })

  it("renders user rows and protects the current user from deactivation", async () => {
    renderPanel()

    expect(await screen.findByText("member")).toBeInTheDocument()

    const deactivate = screen.getAllByRole("button", { name: t.actions.deactivate })
    expect(deactivate).toHaveLength(2)
    expect(deactivate[0]).toBeDisabled()
    expect(deactivate[1]).not.toBeDisabled()
  })

  it("deactivates another user", async () => {
    renderPanel()

    const deactivate = await screen.findAllByRole("button", { name: t.actions.deactivate })
    fireEvent.click(deactivate[1]!)

    await waitFor(() => {
      expect(mocks.setActiveMutateAsync).toHaveBeenCalledWith({ userId: "u2", isActive: false })
    })
  })

  it("sends a test notification", async () => {
    renderPanel()

    const sendTest = await screen.findAllByRole("button", { name: t.actions.sendTest })
    fireEvent.click(sendTest[1]!)

    await waitFor(() => {
      expect(mocks.sendTestMutateAsync).toHaveBeenCalledWith("u2")
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith(t.testSent)
  })
})
