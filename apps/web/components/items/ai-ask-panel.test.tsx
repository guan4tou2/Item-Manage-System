import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/lib/api/client"
import type { AskResponse } from "@/lib/api/ai-search"
import enMessages from "@/messages/en.json"

import { AiAskPanel } from "./ai-ask-panel"

const ask = vi.hoisted(() => ({ mutateAsync: vi.fn(), isPending: false }))

vi.mock("@/lib/hooks/use-ai-search", () => ({
  useAiAsk: () => ask,
}))

function renderPanel(props: Partial<React.ComponentProps<typeof AiAskPanel>> = {}) {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <AiAskPanel itemIds={["item-1"]} {...props} />
    </NextIntlClientProvider>,
  )
}

const grounded: AskResponse = {
  answer: "有 1 件感冒藥[#1]。",
  citations: [{ item_id: "item-1", name: "感冒藥", path: "1F / 廚房 / 藥箱" }],
  grounded: true,
}

describe("AiAskPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ask.isPending = false
  })

  it("asks about the current items and shows the answer with citations", async () => {
    const user = userEvent.setup()
    ask.mutateAsync.mockResolvedValue(grounded)
    renderPanel()

    await user.type(
      screen.getByLabelText("Ask a question about these items"),
      "有哪些快過期？",
    )
    await user.click(screen.getByRole("button", { name: "Ask" }))

    await waitFor(() =>
      expect(ask.mutateAsync).toHaveBeenCalledWith({
        question: "有哪些快過期？",
        itemIds: ["item-1"],
      }),
    )
    expect(await screen.findByText("有 1 件感冒藥[#1]。")).toBeInTheDocument()
    // 引用連結＋路徑
    const link = screen.getByRole("link", { name: /感冒藥/ })
    expect(link).toHaveAttribute("href", "/items/item-1")
    expect(screen.getByText("1F / 廚房 / 藥箱")).toBeInTheDocument()
    // 聲明
    expect(screen.getByText("Answers are limited to your inventory data")).toBeInTheDocument()
  })

  it("marks the answer as AI-generated", async () => {
    const user = userEvent.setup()
    ask.mutateAsync.mockResolvedValue(grounded)
    renderPanel()

    await user.type(screen.getByLabelText("Ask a question about these items"), "？")
    await user.click(screen.getByRole("button", { name: "Ask" }))

    await screen.findByText("有 1 件感冒藥[#1]。")
    expect(screen.getByLabelText("AI-generated, editable")).toBeInTheDocument()
  })

  it("shows the insufficient-data message", async () => {
    const user = userEvent.setup()
    ask.mutateAsync.mockResolvedValue({
      answer: "Not enough data to answer that",
      citations: [],
      grounded: false,
    } as AskResponse)
    renderPanel()

    await user.type(screen.getByLabelText("Ask a question about these items"), "外星人？")
    await user.click(screen.getByRole("button", { name: "Ask" }))

    expect(await screen.findByText("Not enough data to answer that")).toBeInTheDocument()
    expect(screen.queryByText("Sources")).not.toBeInTheDocument()
  })

  it("maps quota and opt-in errors to their messages", async () => {
    const user = userEvent.setup()
    ask.mutateAsync.mockRejectedValueOnce(
      new ApiError(429, { detail: "quota_exhausted" }),
    )
    renderPanel()

    await user.type(screen.getByLabelText("Ask a question about these items"), "？")
    await user.click(screen.getByRole("button", { name: "Ask" }))

    expect(
      await screen.findByText("Today’s AI quota is used up; try again tomorrow"),
    ).toBeInTheDocument()
  })

  it("shows the ai_disabled error", async () => {
    const user = userEvent.setup()
    ask.mutateAsync.mockRejectedValueOnce(new ApiError(503, { detail: "ai_disabled" }))
    renderPanel()

    await user.type(screen.getByLabelText("Ask a question about these items"), "？")
    await user.click(screen.getByRole("button", { name: "Ask" }))

    expect(
      await screen.findByText("AI is not configured; asking is unavailable"),
    ).toBeInTheDocument()
  })

  it("links to settings when opt-in is required", async () => {
    const user = userEvent.setup()
    ask.mutateAsync.mockRejectedValueOnce(
      new ApiError(403, { detail: "ai_opt_in_required" }),
    )
    renderPanel()

    await user.type(screen.getByLabelText("Ask a question about these items"), "？")
    await user.click(screen.getByRole("button", { name: "Ask" }))

    expect(
      await screen.findByText("Enable AI data sharing in settings to ask questions"),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open settings" })).toHaveAttribute(
      "href",
      "/settings/preferences",
    )
  })

  it("does not ask an empty question", async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(screen.getByRole("button", { name: "Ask" }))

    expect(ask.mutateAsync).not.toHaveBeenCalled()
  })

  it("shows the thinking label while pending", () => {
    ask.isPending = true
    renderPanel()

    expect(screen.getByRole("button", { name: "Thinking…" })).toBeDisabled()
  })
})
