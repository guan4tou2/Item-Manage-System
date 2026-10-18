import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import { TagsPanel } from "./tags-panel"

vi.mock("@/lib/hooks/use-tags", () => ({
  useTagsWithCounts: () => ({
    data: [
      { id: 1, name: "home", item_count: 3 },
      { id: 2, name: "travel", item_count: 0 },
    ],
  }),
  useRenameTag: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useMergeTag: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteTag: () => ({ mutateAsync: vi.fn(), isPending: false }),
  usePruneOrphanTags: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), message: vi.fn() },
}))

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <TagsPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("TagsPanel read-only viewer (Phase 30)", () => {
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("keeps tags visible but hides all tag edit entries for viewers", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "viewer-1", is_read_only: true } as never,
    })
    renderPanel()

    expect(screen.getByText("home")).toBeInTheDocument()
    expect(screen.getByText("travel")).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Prune orphan tags" }),
    ).not.toBeInTheDocument()
    expect(screen.queryAllByRole("button", { name: "Rename" })).toHaveLength(0)
    expect(
      screen.queryAllByRole("button", { name: "Merge into another tag" }),
    ).toHaveLength(0)
    expect(screen.queryAllByRole("button", { name: "Delete" })).toHaveLength(0)
  })

  it("keeps all tag edit entries for writers (zero regression)", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "writer-1", is_read_only: false } as never,
    })
    renderPanel()

    expect(screen.getByRole("button", { name: "Prune orphan tags" })).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: "Rename" })).toHaveLength(2)
    expect(screen.getAllByRole("button", { name: "Delete" })).toHaveLength(2)
  })
})
