import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/lib/api/client"
import type { SearchResponse } from "@/lib/api/ai-search"
import enMessages from "@/messages/en.json"

import { AiSearchBar } from "./ai-search-bar"

const search = vi.hoisted(() => ({ mutateAsync: vi.fn() }))

vi.mock("@/lib/hooks/use-ai-search", () => ({
  useAiSearch: () => ({ mutateAsync: search.mutateAsync, isPending: false }),
}))

const push = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}))

function response(overrides: Partial<SearchResponse> = {}): SearchResponse {
  return {
    filters: {
      q: "藥",
      category_id: null,
      location_id: null,
      tag_ids: [],
      expiry: null,
      loan: null,
      favorite: null,
      min_quantity: null,
      max_quantity: null,
      sort: null,
    },
    applied: {
      q: "藥",
      category: null,
      location: null,
      tags: [],
      expiry: null,
      loan: null,
      favorite: null,
      min_quantity: null,
      max_quantity: null,
      sort: null,
    },
    unresolved: [],
    items: [],
    total: 0,
    fallback_reason: null,
    ...overrides,
  } as SearchResponse
}

function renderBar(props: Partial<React.ComponentProps<typeof AiSearchBar>> = {}) {
  const onResults = vi.fn()
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <AiSearchBar onResults={onResults} {...props} />
    </NextIntlClientProvider>,
  )
  return { onResults }
}

describe("AiSearchBar", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("submits the sentence and reports results", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(response())
    const { onResults } = renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "廚房裡的藥")
    await user.click(screen.getByRole("button", { name: "Search" }))

    await waitFor(() => expect(search.mutateAsync).toHaveBeenCalledWith("廚房裡的藥"))
    await waitFor(() => expect(onResults).toHaveBeenCalledWith(expect.objectContaining({ total: 0 })))
  })

  it("renders the understood filters as chips", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(
      response({
        filters: {
          q: "藥",
          category_id: 3,
          location_id: 7,
          tag_ids: [11],
          expiry: "expiring_soon",
          loan: "borrowed",
          favorite: null,
          min_quantity: 1,
          max_quantity: 5,
          sort: "expiry_asc",
        },
        applied: {
          q: "藥",
          category: { id: 3, name: "藥品", path: null },
          location: { id: 7, name: "廚房", path: "1F / 廚房" },
          tags: [{ id: 11, name: "重要", path: null }],
          expiry: "expiring_soon",
          loan: "borrowed",
          favorite: null,
          min_quantity: 1,
          max_quantity: 5,
          sort: "expiry_asc",
        },
      }),
    )
    renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "廚房裡快過期的藥")
    await user.click(screen.getByRole("button", { name: "Search" }))

    expect(await screen.findByText("Understood as")).toBeInTheDocument()
    expect(screen.getByText("Keyword: 藥")).toBeInTheDocument()
    expect(screen.getByText("Category: 藥品")).toBeInTheDocument()
    expect(screen.getByText("Location: 1F / 廚房")).toBeInTheDocument()
    expect(screen.getByText("Tags: 重要")).toBeInTheDocument()
    expect(screen.getByText("Expiry: within 7 days")).toBeInTheDocument()
    expect(screen.getByText("Loans: lent out")).toBeInTheDocument()
    expect(screen.getByText("Quantity: 1–5")).toBeInTheDocument()
    expect(screen.getByText("Sort: soonest expiry")).toBeInTheDocument()
  })

  it("marks unresolved names without blocking the other filters", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(
      response({
        applied: {
          q: null,
          category: null,
          location: null,
          tags: [],
          expiry: null,
          loan: null,
          favorite: null,
          min_quantity: null,
          max_quantity: null,
          sort: null,
        },
        unresolved: ["category:露營裝備"],
      }),
    )
    renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "露營裝備")
    await user.click(screen.getByRole("button", { name: "Search" }))

    expect(await screen.findByText("Not found: 露營裝備")).toBeInTheDocument()
  })

  it("explains the keyword fallback without an error state", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(response({ fallback_reason: "ai_disabled" }))
    renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "藥")
    await user.click(screen.getByRole("button", { name: "Search" }))

    expect(
      await screen.findByText("AI is not configured; showing keyword results instead"),
    ).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("prompts to enable data sharing when opt-in is required", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockRejectedValue(
      new ApiError(403, { detail: "ai_opt_in_required" }),
    )
    renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "藥")
    await user.click(screen.getByRole("button", { name: "Search" }))

    expect(
      await screen.findByText("Enable AI data sharing in settings to use AI search"),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open settings" })).toHaveAttribute(
      "href",
      "/settings/preferences",
    )
  })

  it("clears the understood filters", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(response())
    const { onResults } = renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "藥")
    await user.click(screen.getByRole("button", { name: "Search" }))
    await screen.findByText("Understood as")

    await user.click(screen.getByRole("button", { name: "Clear" }))

    expect(screen.queryByText("Understood as")).not.toBeInTheDocument()
    expect(onResults).toHaveBeenLastCalledWith(null)
  })

  it("opens the understood filters in the item list", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(
      response({
        total: 1,
        applied: {
          q: "藥",
          category: null,
          location: { id: 7, name: "廚房", path: "1F / 廚房" },
          tags: [],
          expiry: "expiring_soon",
          loan: null,
          favorite: null,
          min_quantity: null,
          max_quantity: null,
          sort: null,
        },
      }),
    )
    renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "廚房裡的藥")
    await user.click(screen.getByRole("button", { name: "Search" }))
    await screen.findByText("Understood as")

    await user.click(screen.getByRole("button", { name: "Open in item list" }))

    expect(push).toHaveBeenCalledWith("/items?q=%E8%97%A5&location=7&expiry=expiring_soon")
  })

  it("shows the no-results hint", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(response())
    renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "不存在")
    await user.click(screen.getByRole("button", { name: "Search" }))

    expect(await screen.findByText("No matches — try rephrasing")).toBeInTheDocument()
  })

  it("shows the result count without leaking translation keys", async () => {
    const user = userEvent.setup()
    search.mutateAsync.mockResolvedValue(response({ total: 3 }))
    renderBar()

    await user.type(screen.getByLabelText("Describe what you are looking for"), "藥")
    await user.click(screen.getByRole("button", { name: "Search" }))

    expect(await screen.findByText("3 result(s)")).toBeInTheDocument()
    expect(screen.queryByText(/items\.list/)).not.toBeInTheDocument()
  })

  it("does not submit an empty sentence", async () => {
    const user = userEvent.setup()
    renderBar()

    await user.click(screen.getByRole("button", { name: "Search" }))

    expect(search.mutateAsync).not.toHaveBeenCalled()
  })
})
