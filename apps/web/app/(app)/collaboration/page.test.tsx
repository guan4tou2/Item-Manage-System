import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import CollaborationPage from "./page"

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/hooks/use-groups", () => ({
  useGroups: () => ({ data: [], isLoading: false }),
  useCreateGroup: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock("@/lib/hooks/use-transfers", () => ({
  useTransfers: () => ({ data: [], isLoading: false }),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <CollaborationPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("CollaborationPage read-only viewer (Phase 30)", () => {
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("hides the new-group entry for viewers", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "viewer-1", is_read_only: true } as never,
    })
    renderPage()

    expect(screen.queryByRole("button", { name: "New group" })).not.toBeInTheDocument()
  })

  it("keeps the new-group entry for writers (zero regression)", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "writer-1", is_read_only: false } as never,
    })
    renderPage()

    expect(screen.getByRole("button", { name: "New group" })).toBeInTheDocument()
  })
})
