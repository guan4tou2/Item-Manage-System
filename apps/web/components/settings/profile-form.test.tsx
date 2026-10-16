import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { ProfileForm } from "./profile-form"

const mocks = vi.hoisted(() => ({
  updateMutateAsync: vi.fn(),
  // 穩定引用：ProfileForm 的 useEffect 依賴 me.data，每次 render 回新物件會重置輸入。
  meData: { id: "u1", email: "member@example.com", username: "member", is_admin: false },
}))

vi.mock("@/lib/hooks/use-profile", () => ({
  useMe: () => ({ isLoading: false, data: mocks.meData }),
  useUpdateProfile: () => ({ mutateAsync: mocks.updateMutateAsync, isPending: false }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.profile

function renderForm() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <ProfileForm />
    </NextIntlClientProvider>,
  )
}

describe("ProfileForm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.updateMutateAsync.mockResolvedValue({})
  })

  it("prefills the fields from the current profile", () => {
    renderForm()

    expect(screen.getByLabelText(t.email)).toHaveValue("member@example.com")
    expect(screen.getByLabelText(t.username)).toHaveValue("member")
  })

  it("submits edited values and toasts success", async () => {
    renderForm()

    fireEvent.change(screen.getByLabelText(t.username), { target: { value: "newname" } })
    fireEvent.click(screen.getByRole("button", { name: t.save }))

    await waitFor(() => {
      expect(mocks.updateMutateAsync).toHaveBeenCalledWith({
        email: "member@example.com",
        username: "newname",
      })
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith(t.saved)
  })

  it("toasts a conflict error when the update fails", async () => {
    mocks.updateMutateAsync.mockRejectedValue(new Error("conflict"))
    renderForm()

    fireEvent.click(screen.getByRole("button", { name: t.save }))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith(t.conflict)
    })
  })
})
