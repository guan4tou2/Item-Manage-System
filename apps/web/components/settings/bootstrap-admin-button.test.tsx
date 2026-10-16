import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { BootstrapAdminButton } from "./bootstrap-admin-button"

const mocks = vi.hoisted(() => ({
  me: vi.fn(),
  mutateAsync: vi.fn(),
}))

vi.mock("@/lib/hooks/use-profile", () => ({
  useMe: mocks.me,
  useBootstrapAdmin: () => ({ mutateAsync: mocks.mutateAsync, isPending: false }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.bootstrap

function renderButton() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <BootstrapAdminButton />
    </NextIntlClientProvider>,
  )
}

describe("BootstrapAdminButton", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.mutateAsync.mockResolvedValue({})
    mocks.me.mockReturnValue({ isLoading: false, data: { is_admin: false } })
  })

  it("prompts non-admins and promotes on click", async () => {
    renderButton()

    expect(screen.getByText(t.prompt)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: t.confirm }))

    await waitFor(() => expect(mocks.mutateAsync).toHaveBeenCalledTimes(1))
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith(t.success)
  })

  it("renders nothing for admins", () => {
    mocks.me.mockReturnValue({ isLoading: false, data: { is_admin: true } })
    const { container } = renderButton()

    expect(container).toBeEmptyDOMElement()
  })

  it("toasts an error when promotion fails", async () => {
    mocks.mutateAsync.mockRejectedValue(new Error("admin already exists"))
    renderButton()

    fireEvent.click(screen.getByRole("button", { name: t.confirm }))

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalled())
  })
})
