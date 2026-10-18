import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { useAuthStore } from "@/lib/auth/auth-store"

import { ViewerBanner } from "./viewer-banner"

const prefsState: {
  value: { data?: { viewer_notice_dismissed?: boolean }; isLoading: boolean }
} = { value: { data: { viewer_notice_dismissed: false }, isLoading: false } }

const mutate = vi.fn()

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: () => prefsState.value,
  useUpdatePreferences: () => ({ mutate, isPending: false }),
}))

const toastError = vi.fn()
vi.mock("sonner", () => ({ toast: { error: (m: string) => toastError(m) } }))

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

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

describe("ViewerBanner", () => {
  beforeEach(() => {
    mutate.mockClear()
    toastError.mockClear()
    prefsState.value = { data: { viewer_notice_dismissed: false }, isLoading: false }
    useAuthStore.setState({ accessToken: "jwt", user: user(true) })
  })

  it("shows one-time notice for a viewer", () => {
    render(<ViewerBanner />, { wrapper: Provider })
    expect(screen.getByTestId("viewer-banner")).toHaveTextContent("You are a viewer")
  })

  it("hides after dismissal preference is set", () => {
    prefsState.value = { data: { viewer_notice_dismissed: true }, isLoading: false }
    render(<ViewerBanner />, { wrapper: Provider })
    expect(screen.queryByTestId("viewer-banner")).not.toBeInTheDocument()
  })

  it("hides for non-viewer", () => {
    useAuthStore.setState({ accessToken: "jwt", user: user(false) })
    render(<ViewerBanner />, { wrapper: Provider })
    expect(screen.queryByTestId("viewer-banner")).not.toBeInTheDocument()
  })

  it("hides while preferences are loading (no flash)", () => {
    prefsState.value = { data: undefined, isLoading: true }
    render(<ViewerBanner />, { wrapper: Provider })
    expect(screen.queryByTestId("viewer-banner")).not.toBeInTheDocument()
  })

  it("persists dismissal via preferences when dismissed", async () => {
    const u = userEvent.setup()
    render(<ViewerBanner />, { wrapper: Provider })
    await u.click(screen.getByRole("button", { name: "Got it" }))
    expect(mutate).toHaveBeenCalledTimes(1)
    expect(mutate.mock.calls[0]?.[0]).toEqual({ viewer_notice_dismissed: true })
  })

  it("invokes error handling on failure", async () => {
    const u = userEvent.setup()
    render(<ViewerBanner />, { wrapper: Provider })
    await u.click(screen.getByRole("button", { name: "Got it" }))
    const options = mutate.mock.calls[0]?.[1] as { onError: () => void } | undefined
    options?.onError()
    expect(toastError).toHaveBeenCalledWith(
      "Could not dismiss the notice; please try again",
    )
  })
})
