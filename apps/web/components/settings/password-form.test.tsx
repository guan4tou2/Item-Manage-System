import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { PasswordForm } from "./password-form"

const mocks = vi.hoisted(() => ({
  changeMutateAsync: vi.fn(),
}))

vi.mock("@/lib/hooks/use-profile", () => ({
  useChangePassword: () => ({ mutateAsync: mocks.changeMutateAsync, isPending: false }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.password

function renderForm() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <PasswordForm />
    </NextIntlClientProvider>,
  )
}

function fill(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText(t.current), { target: { value: current } })
  fireEvent.change(screen.getByLabelText(t.new), { target: { value: next } })
  fireEvent.change(screen.getByLabelText(t.confirm), { target: { value: confirm } })
}

describe("PasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.changeMutateAsync.mockResolvedValue(undefined)
  })

  it("blocks submission when the confirmation does not match", () => {
    renderForm()

    fill("oldpass123", "newpass123", "different1")

    expect(screen.getByText(t.mismatch)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: t.save })).toBeDisabled()
    expect(mocks.changeMutateAsync).not.toHaveBeenCalled()
  })

  it("submits a valid password change and toasts success", async () => {
    renderForm()

    fill("oldpass123", "newpass123", "newpass123")
    fireEvent.click(screen.getByRole("button", { name: t.save }))

    await waitFor(() => {
      expect(mocks.changeMutateAsync).toHaveBeenCalledWith({
        current_password: "oldpass123",
        new_password: "newpass123",
      })
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith(t.saved)
  })

  it("toasts the wrong-current-password error on failure", async () => {
    mocks.changeMutateAsync.mockRejectedValue(new Error("401"))
    renderForm()

    fill("badpass123", "newpass123", "newpass123")
    fireEvent.click(screen.getByRole("button", { name: t.save }))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(t.wrongCurrent)
    })
  })
})
