import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import { LogoutAllSection } from "./logout-all-section"

const mocks = vi.hoisted(() => ({ push: vi.fn() }))

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mocks.push }) }))
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

const t = enMessages.settings.password.logoutAll
const originalFetch = global.fetch

function renderSection() {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <LogoutAllSection />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("LogoutAllSection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ accessToken: "jwt", user: null })
  })
  afterEach(() => {
    global.fetch = originalFetch
  })

  it("asks for confirmation, calls logout-all, clears the store and redirects", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    global.fetch = fetchMock
    renderSection()

    fireEvent.click(screen.getByRole("button", { name: t.button }))
    expect(fetchMock).not.toHaveBeenCalled()
    fireEvent.click(await screen.findByRole("button", { name: t.confirm }))

    await waitFor(() => expect(mocks.push).toHaveBeenCalledWith("/login"))
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toMatch(/\/auth\/logout-all$/)
    expect(init.method).toBe("POST")
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("does nothing when the dialog is cancelled", async () => {
    const fetchMock = vi.fn()
    global.fetch = fetchMock
    renderSection()

    fireEvent.click(screen.getByRole("button", { name: t.button }))
    fireEvent.click(await screen.findByRole("button", { name: t.cancel }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(mocks.push).not.toHaveBeenCalled()
  })

  it("toasts an error and stays on the page when the request fails", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "boom" }), { status: 500 }))
    renderSection()

    fireEvent.click(screen.getByRole("button", { name: t.button }))
    fireEvent.click(await screen.findByRole("button", { name: t.confirm }))

    await waitFor(() => expect(vi.mocked(toast.error)).toHaveBeenCalledWith(t.failed))
    expect(mocks.push).not.toHaveBeenCalled()
    expect(useAuthStore.getState().accessToken).toBe("jwt")
  })
})
