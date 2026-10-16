import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as api from "@/lib/api/api-tokens"
import enMessages from "@/messages/en.json"

import { ApiTokensPanel } from "./api-tokens-panel"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/api-tokens", () => ({
  createToken: vi.fn(),
  deleteToken: vi.fn(),
  listTokens: vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.tokens

const existingToken = {
  id: "t1",
  name: "CI",
  last_used_at: null,
  created_at: "2026-10-01T00:00:00Z",
}

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ApiTokensPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("ApiTokensPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listTokens).mockResolvedValue([existingToken])
    vi.mocked(api.createToken).mockResolvedValue({
      ...existingToken,
      id: "t2",
      name: "Mobile",
      token: "tok_secret",
    })
    vi.mocked(api.deleteToken).mockResolvedValue(undefined)
  })

  it("lists existing tokens", async () => {
    renderPanel()

    expect(await screen.findByText("CI")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: t.delete })).toBeInTheDocument()
  })

  it("creates a token and reveals it once", async () => {
    renderPanel()

    fireEvent.change(screen.getByPlaceholderText(t.namePlaceholder), {
      target: { value: "Mobile" },
    })
    fireEvent.click(screen.getByRole("button", { name: t.create }))

    expect(await screen.findByText("tok_secret")).toBeInTheDocument()
    expect(screen.getByText(t.created)).toBeInTheDocument()
    expect(vi.mocked(api.createToken)).toHaveBeenCalledWith("Mobile", "jwt")
  })

  it("deletes a token", async () => {
    renderPanel()

    fireEvent.click(await screen.findByRole("button", { name: t.delete }))

    await waitFor(() => {
      expect(vi.mocked(api.deleteToken)).toHaveBeenCalledWith("t1", "jwt")
    })
  })
})
