import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"
import type { DraftRead } from "@/lib/api/ai-drafts"
import type { CategoryTreeNode } from "@/lib/api/categories"
import type { LocationRead } from "@/lib/api/locations"

import { DraftCard } from "./draft-card"

const mocks = vi.hoisted(() => ({ suggest: vi.fn() }))

vi.mock("@/lib/hooks/use-ai-drafts", () => ({
  useSuggestClassification: () => ({ mutateAsync: mocks.suggest }),
}))

vi.mock("@/lib/hooks/use-locations", () => ({ useLocations: () => ({ data: [] }) }))
vi.mock("@/lib/hooks/use-is-mobile", () => ({ useIsMobile: () => false }))

const categories: CategoryTreeNode[] = [
  {
    id: 3,
    name: "Kitchen",
    parent_id: null,
    children: [{ id: 4, name: "Mugs", parent_id: 3, children: [] }],
  },
  { id: 9, name: "Storage", parent_id: null, children: [] },
]

const locations: LocationRead[] = [
  {
    id: 7,
    parent_id: null,
    name: "Kitchen shelf",
    kind: null,
    sort_order: 0,
    floor_plan_image_id: null,
    path: "Kitchen shelf",
  },
]

const noSuggestions = { category: null, location: null, tags: [] }

function draftOf(overrides: Partial<DraftRead> = {}): DraftRead {
  return {
    id: "draft-1",
    source: "batch_photo",
    status: "pending",
    image_id: "img-1",
    item_id: null,
    error_code: null,
    payload: {
      version: 1,
      ai: null,
      history: { category: null, location: null, tags: [] },
    },
    processed_at: null,
    created_at: "2026-10-19T02:11:03Z",
    ...overrides,
  }
}

const readyDraft = draftOf({
  status: "ready",
  processed_at: "2026-10-19T02:11:09Z",
  payload: {
    version: 1,
    ai: {
      name: "Coffee dripper",
      description: "Ceramic pour-over",
      category_suggestion: "Kitchen",
      tag_suggestions: ["coffee"],
    },
    history: {
      category: { id: 3, name: "Kitchen", item_count: 12, score: 4 },
      location: { id: 7, name: "Kitchen shelf", item_count: 9, score: 3 },
      tags: [{ name: "coffee", item_count: 6, score: 3 }],
    },
  },
})

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const zhProvider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="zh-TW" messages={zhMessages}>
    {children}
  </NextIntlClientProvider>
)

function renderCard(props: Partial<React.ComponentProps<typeof DraftCard>> = {}, wrapper = Provider) {
  const handlers = {
    onProcess: vi.fn(),
    onAccept: vi.fn(),
    onDiscard: vi.fn(),
  }
  const view = render(
    <DraftCard
      draft={draftOf()}
      categories={categories}
      locations={locations}
      tagSuggestions={["coffee", "tea"]}
      {...handlers}
      {...props}
    />,
    { wrapper },
  )
  return { ...view, ...handlers }
}

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

beforeEach(() => {
  mocks.suggest.mockReset()
})

describe("DraftCard 四態", () => {
  it("shows the queued state for pending drafts", () => {
    renderCard({ draft: draftOf({ status: "pending" }) })

    const card = screen.getByTestId("draft-card-draft-1")
    expect(card).toHaveAttribute("data-status", "pending")
    expect(within(card).getByText("Queued")).toBeInTheDocument()
    expect(within(card).queryByRole("button", { name: "Accept" })).not.toBeInTheDocument()
  })

  it("shows a busy state with a re-process action while processing", async () => {
    const user = userEvent.setup()
    const { onProcess } = renderCard({ draft: draftOf({ status: "processing" }) })

    expect(screen.getByText("Recognizing…")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Recognize again" }))
    expect(onProcess).toHaveBeenCalledWith("draft-1")
  })

  it("renders the failure reason with retry and a manual fill toggle", async () => {
    const user = userEvent.setup()
    const { onProcess } = renderCard({
      draft: draftOf({ status: "failed", error_code: "ai_disabled" }),
    })

    expect(screen.getByRole("alert")).toHaveTextContent("AI is not configured")
    await user.click(screen.getByRole("button", { name: "Retry recognition" }))
    expect(onProcess).toHaveBeenCalledWith("draft-1")

    // 手動填寫：預設收起，展開後可輸入並接受
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument()
    const toggle = screen.getByRole("button", { name: "Fill in manually" })
    expect(toggle).toHaveAttribute("aria-expanded", "false")
    await user.click(toggle)
    expect(toggle).toHaveAttribute("aria-expanded", "true")

    const accept = screen.getByRole("button", { name: "Accept" })
    expect(accept).toBeDisabled()
    await user.type(screen.getByLabelText("Name"), "Coffee dripper")
    expect(accept).toBeEnabled()
  })

  it("maps every error code to localized copy", () => {
    const cases: Array<[DraftRead["error_code"], string]> = [
      ["quota_exhausted", "Today's AI quota is used up"],
      ["upstream_error", "The AI service is temporarily unavailable"],
      ["image_missing", "The photo no longer exists"],
    ]
    for (const [code, copy] of cases) {
      const { unmount } = renderCard({
        draft: draftOf({ status: "failed", error_code: code }),
      })
      expect(screen.getByRole("alert")).toHaveTextContent(copy)
      unmount()
    }
  })

  it("uses zh-TW copy for the error and mark", () => {
    renderCard(
      { draft: draftOf({ status: "failed", error_code: "ai_disabled" }) },
      zhProvider,
    )

    expect(screen.getByRole("alert")).toHaveTextContent("AI 未設定")
    expect(screen.getByText("辨識失敗")).toBeInTheDocument()
  })
})

describe("DraftCard 建議預設與編輯", () => {
  it("prefills AI fields with the mark and history badges", () => {
    renderCard({ draft: readyDraft })

    expect(screen.getByLabelText("Name")).toHaveValue("Coffee dripper")
    expect(screen.getByLabelText("Description")).toHaveValue("Ceramic pour-over")
    // AI 產出欄位旁 ✦ 標記（2 個：名稱、描述）
    expect(screen.getAllByRole("img", { name: "AI-generated, editable" })).toHaveLength(2)
    expect(screen.getByTestId("draft-history-category-badge")).toHaveTextContent(
      "From history: Kitchen",
    )
    expect(screen.getByTestId("draft-history-location-badge")).toHaveTextContent(
      "From history: Kitchen shelf",
    )
    expect(screen.getByTestId("draft-history-tags-badge")).toHaveTextContent(
      "From history: coffee",
    )
  })

  it("accepts the seeded values without extra edits", async () => {
    const user = userEvent.setup()
    const { onAccept } = renderCard({ draft: readyDraft })

    await user.click(screen.getByRole("button", { name: "Accept" }))

    expect(onAccept).toHaveBeenCalledWith("draft-1", {
      name: "Coffee dripper",
      description: "Ceramic pour-over",
      category_id: 3,
      location_id: 7,
      tag_names: ["coffee"],
      quantity: 1,
      cost: null,
    })
  })

  it("sends edited values and drops blank optional fields", async () => {
    const user = userEvent.setup()
    const { onAccept } = renderCard({ draft: readyDraft })

    await user.clear(screen.getByLabelText("Name"))
    await user.type(screen.getByLabelText("Name"), "  V60 dripper  ")
    await user.clear(screen.getByLabelText("Quantity"))
    await user.type(screen.getByLabelText("Quantity"), "2")
    await user.type(screen.getByLabelText("Cost"), "450")
    await user.click(screen.getByRole("button", { name: "Accept" }))

    expect(onAccept).toHaveBeenCalledWith(
      "draft-1",
      expect.objectContaining({ name: "V60 dripper", quantity: 2, cost: "450" }),
    )
  })

  it("falls back to the AI category name when history has none", () => {
    renderCard({
      draft: draftOf({
        status: "ready",
        payload: {
          version: 1,
          ai: {
            name: "Mug",
            description: null,
            category_suggestion: "Mugs",
            tag_suggestions: [],
          },
          history: { category: null, location: null, tags: [] },
        },
      }),
    })

    // 「Mugs」為巢狀分類的完整名稱 → 精確同名匹配
    expect(screen.getByTestId("draft-category-select")).toHaveTextContent("— Mugs")
    expect(screen.queryByTestId("draft-history-category-badge")).not.toBeInTheDocument()
  })

  it("keeps fields empty when neither history nor AI suggest them", () => {
    renderCard({
      draft: draftOf({
        status: "ready",
        payload: {
          version: 1,
          ai: { name: "", description: null, category_suggestion: null, tag_suggestions: [] },
          history: { category: null, location: null, tags: [] },
        },
      }),
    })

    expect(screen.getByLabelText("Name")).toHaveValue("")
    expect(screen.getByRole("button", { name: "Accept" })).toBeDisabled()
  })

  it("applies classifications from the suggest button", async () => {
    const user = userEvent.setup()
    mocks.suggest.mockResolvedValue({
      category: { id: 9, name: "Storage", item_count: 4, score: 2 },
      location: null,
      tags: [{ name: "tea", item_count: 2, score: 1 }],
    })
    const { onAccept } = renderCard({
      draft: draftOf({
        status: "ready",
        payload: {
          version: 1,
          ai: { name: "Tea tin", description: null, category_suggestion: null, tag_suggestions: [] },
          history: { category: null, location: null, tags: [] },
        },
      }),
    })

    await user.click(screen.getByRole("button", { name: "Suggest from history" }))

    expect(mocks.suggest).toHaveBeenCalledWith("Tea tin")
    expect(screen.getByTestId("draft-history-category-badge")).toHaveTextContent(
      "From history: Storage",
    )
    await user.click(screen.getByRole("button", { name: "Accept" }))
    expect(onAccept).toHaveBeenCalledWith(
      "draft-1",
      expect.objectContaining({ category_id: 9, location_id: null, tag_names: ["tea"] }),
    )
  })

  it("explains when the history lookup finds nothing", async () => {
    const user = userEvent.setup()
    mocks.suggest.mockResolvedValue(noSuggestions)
    renderCard({
      draft: draftOf({
        status: "ready",
        payload: {
          version: 1,
          ai: { name: "Mystery box", description: null, category_suggestion: null, tag_suggestions: [] },
          history: { category: null, location: null, tags: [] },
        },
      }),
    })

    await user.click(screen.getByRole("button", { name: "Suggest from history" }))

    expect(await screen.findByText("No matching history found")).toBeInTheDocument()
  })

  it("disables the suggest button without a name", () => {
    renderCard({
      draft: draftOf({
        status: "ready",
        payload: {
          version: 1,
          ai: { name: "", description: null, category_suggestion: null, tag_suggestions: [] },
          history: { category: null, location: null, tags: [] },
        },
      }),
    })

    expect(screen.getByRole("button", { name: "Suggest from history" })).toBeDisabled()
  })

  it("discards the draft", async () => {
    const user = userEvent.setup()
    const { onDiscard } = renderCard({ draft: readyDraft })

    await user.click(screen.getByRole("button", { name: "Discard" }))

    expect(onDiscard).toHaveBeenCalledWith("draft-1")
  })

  it("marks card actions as busy while accepting or discarding", () => {
    renderCard({ draft: readyDraft, accepting: true })

    expect(screen.getByRole("button", { name: "Accepting…" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Discard" })).toBeDisabled()
  })

  it("toggles bulk selection through the checkbox", async () => {
    const user = userEvent.setup()
    const onSelectedChange = vi.fn()
    renderCard({ draft: readyDraft, selected: false, onSelectedChange })

    await user.click(screen.getByRole("checkbox", { name: "Select draft Coffee dripper" }))

    expect(onSelectedChange).toHaveBeenCalledWith(true)
  })
})
