import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/lib/api/client"
import enMessages from "@/messages/en.json"

import { LoginForm } from "./login-form"

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  push: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useLogin: () => ({
    mutateAsync: mocks.mutateAsync,
    isPending: false,
  }),
}))

function renderForm() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <LoginForm />
    </NextIntlClientProvider>,
  )
}

function submit(username: string, password: string) {
  fireEvent.change(screen.getByLabelText(enMessages.login.username), {
    target: { value: username },
  })
  fireEvent.change(screen.getByLabelText(enMessages.login.password), {
    target: { value: password },
  })
  fireEvent.click(
    screen.getByRole("button", { name: enMessages.login.submit }),
  )
}

describe("LoginForm error copy", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows the rate-limit message on 429", async () => {
    mocks.mutateAsync.mockRejectedValue(
      new ApiError(429, { detail: "too many login attempts" }),
    )

    renderForm()
    submit("alice", "secret1234")

    expect(await screen.findByRole("alert")).toHaveTextContent(
      enMessages.login.tooManyAttempts,
    )
  })

  it("keeps the generic message on 401", async () => {
    mocks.mutateAsync.mockRejectedValue(
      new ApiError(401, { detail: "invalid credentials" }),
    )

    renderForm()
    submit("alice", "wrong-pass")

    expect(await screen.findByRole("alert")).toHaveTextContent(
      enMessages.login.error,
    )
  })

  it("navigates to the dashboard on success", async () => {
    mocks.mutateAsync.mockResolvedValue({ access_token: "token", user: {} })

    renderForm()
    submit("alice", "secret1234")

    await vi.waitFor(() => {
      expect(mocks.push).toHaveBeenCalledWith("/dashboard")
    })
  })
})
