import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, describe, expect, it, vi } from "vitest"

import { useAuthStore } from "@/lib/auth/auth-store"
import enMessages from "@/messages/en.json"

import ListDetailPage from "./page"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "l1" }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

const listDetail = {
  id: "l1",
  kind: "travel",
  title: "Japan trip",
  description: null,
  start_date: null,
  end_date: null,
  budget: null,
  currency: "TWD",
  entry_count: 1,
  done_count: 0,
  created_at: "2026-04-23T00:00:00Z",
  updated_at: "2026-04-23T00:00:00Z",
  entries: [
    {
      id: "e1",
      list_id: "l1",
      position: 0,
      name: "Passport",
      quantity: 2,
      note: null,
      price: null,
      link: null,
      is_done: false,
      created_at: "2026-04-23T00:00:00Z",
      updated_at: "2026-04-23T00:00:00Z",
    },
  ],
}

vi.mock("@/lib/hooks/use-lists", () => ({
  useList: () => ({ data: listDetail, isLoading: false, isError: false }),
  useCreateEntry: () => ({ isPending: false, mutate: vi.fn() }),
  useToggleEntry: () => ({ mutate: vi.fn() }),
  useDeleteEntry: () => ({ mutate: vi.fn() }),
  useDeleteList: () => ({ mutateAsync: vi.fn() }),
  useReorderEntries: () => ({ mutate: vi.fn() }),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <ListDetailPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("ListDetailPage read-only viewer (Phase 30)", () => {
  afterEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it("renders entries read-only without any edit entry", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "viewer-1", is_read_only: true } as never,
    })
    renderPage()

    // 資料列仍可見（含完成狀態）
    expect(screen.getByText("Passport")).toBeInTheDocument()
    const checkbox = screen.getByRole("checkbox", { name: "Passport" })
    expect(checkbox).toBeDisabled()
    // 無刪除清單、無新增項目表單、無項目刪除、無拖放把手
    expect(screen.queryAllByRole("button", { name: "Delete list" })).toHaveLength(0)
    expect(screen.queryByRole("button", { name: "Create" })).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Drag to reorder")).not.toBeInTheDocument()
  })

  it("keeps all edit entries for writers (zero regression)", () => {
    useAuthStore.setState({
      accessToken: "jwt",
      user: { id: "writer-1", is_read_only: false } as never,
    })
    renderPage()

    expect(
      screen.getAllByRole("button", { name: "Delete list" }).length,
    ).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument()
    expect(screen.getByRole("checkbox", { name: "Passport" })).toBeEnabled()
    expect(screen.getByLabelText("Drag to reorder")).toBeInTheDocument()
  })
})
