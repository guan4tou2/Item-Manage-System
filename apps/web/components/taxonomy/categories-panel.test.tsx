import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import { CategoriesPanel } from "./categories-panel"

const hooks = vi.hoisted(() => ({ create: vi.fn(), remove: vi.fn() }))

vi.mock("@/lib/hooks/use-categories", () => ({
  useCategories: () => ({
    data: [
      {
        id: 1,
        name: "Home",
        parent_id: null,
        children: [{ id: 2, name: "Kitchen", parent_id: 1, children: [] }],
      },
    ],
    isLoading: false,
  }),
  useCreateCategory: () => hooks.create(),
  useDeleteCategory: () => hooks.remove(),
}))

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <CategoriesPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("CategoriesPanel read-only viewer (Phase 30)", () => {
  beforeEach(() => {
    hooks.create.mockReturnValue({ mutate: vi.fn(), isPending: false })
    hooks.remove.mockReturnValue({ mutate: vi.fn(), isPending: false })
  })

  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("keeps the tree visible but hides add and delete entries for viewers", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "viewer-1", is_read_only: true } as never,
    })
    renderPanel()

    expect(screen.getByText("Home")).toBeInTheDocument()
    expect(screen.getByText("— Kitchen")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Add category" })).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument()
    expect(screen.queryAllByRole("button", { name: "Delete" })).toHaveLength(0)
  })

  it("keeps add and delete entries for writers (zero regression)", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "writer-1", is_read_only: false } as never,
    })
    renderPanel()

    expect(screen.getByRole("button", { name: "Add category" })).toBeInTheDocument()
    expect(screen.getByLabelText("Name")).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: "Delete" })).toHaveLength(2)
  })
})
