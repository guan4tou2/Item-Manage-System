import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"
import zhMessages from "@/messages/zh-TW.json"

import { AiMark } from "./ai-mark"

function renderMark(locale: "en" | "zh-TW") {
  const messages = locale === "en" ? enMessages : zhMessages
  return render(<AiMark />, {
    wrapper: ({ children }: { children: React.ReactNode }) => (
      <NextIntlClientProvider locale={locale} messages={messages}>
        {children}
      </NextIntlClientProvider>
    ),
  })
}

describe("AiMark", () => {
  it("labels the mark in zh-TW with role=img and a tap target", () => {
    renderMark("zh-TW")

    const mark = screen.getByRole("img", { name: "由 AI 產生，可編輯" })
    expect(mark).toHaveAttribute("aria-label", "由 AI 產生，可編輯")
    // tap／鍵盤可及：可聚焦
    expect(mark.tabIndex).toBe(0)
  })

  it("labels the mark in en", () => {
    renderMark("en")

    expect(screen.getByRole("img", { name: "AI-generated, editable" })).toBeInTheDocument()
  })

  it("renders the sparkles glyph without adding container styles", () => {
    renderMark("zh-TW")

    const mark = screen.getByRole("img", { name: "由 AI 產生，可編輯" })
    expect(mark.className).toContain("text-muted-foreground")
    expect(mark.className).not.toContain("bg-gradient")
    expect(mark.className).not.toContain("animate-")

    const glyph = mark.querySelector("svg")
    expect(glyph).not.toBeNull()
    expect(glyph).toHaveAttribute("aria-hidden", "true")
    expect(glyph?.getAttribute("class")).toContain("size-3.5")
  })

  it("explains itself on hover", async () => {
    const user = userEvent.setup()
    renderMark("zh-TW")

    await user.hover(screen.getByRole("img", { name: "由 AI 產生，可編輯" }))

    expect(await screen.findByRole("tooltip")).toHaveTextContent("由 AI 產生，可編輯")
  })

  it("explains itself on keyboard focus", async () => {
    const user = userEvent.setup()
    renderMark("en")

    await user.tab()

    expect(await screen.findByRole("tooltip")).toHaveTextContent("AI-generated, editable")
  })
})
