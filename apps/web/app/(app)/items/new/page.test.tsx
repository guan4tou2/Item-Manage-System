import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import NewItemPage from "./page"

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("@/components/items/item-form", () => ({
  ItemForm: (props: { itemTemplates?: Array<{ id: number; name: string }> }) => (
    <div>
      {(props.itemTemplates ?? []).map((template) => (
        <button key={template.id} type="button">
          {template.name}
        </button>
      ))}
    </div>
  ),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/hooks/use-categories", () => ({
  useCategories: () => ({ data: [] }),
}))

vi.mock("@/lib/hooks/use-items", () => ({
  useCreateItem: () => ({ isPending: false, mutateAsync: vi.fn() }),
}))

vi.mock("@/lib/hooks/use-locations", () => ({
  useLocations: () => ({ data: [] }),
}))

vi.mock("@/lib/hooks/use-tags", () => ({
  useTags: () => ({ data: [] }),
}))

vi.mock("@/lib/api/customization", () => ({
  listCustomFields: vi.fn().mockResolvedValue([]),
  listItemTemplates: vi.fn().mockResolvedValue([
    {
      id: 10,
      name: "Restock pack",
      payload: { name: "AA Battery", quantity: 12 },
      created_at: "2026-06-19T00:00:00Z",
    },
  ]),
  saveItemCustomValues: vi.fn(),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <NewItemPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("NewItemPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("passes item templates into the item form", async () => {
    renderPage()

    expect(await screen.findByRole("button", { name: "Restock pack" })).toBeInTheDocument()
  })
})
