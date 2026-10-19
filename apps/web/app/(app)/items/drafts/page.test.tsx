import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import DraftsPage from "./page"

vi.mock("./drafts-client", () => ({
  DraftsClient: () => <div data-testid="drafts-client" />,
}))

function renderPage() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <DraftsPage />
    </NextIntlClientProvider>,
  )
}

describe("DraftsPage", () => {
  it("renders the queue shell with the manual-entry escape hatch", () => {
    renderPage()

    expect(screen.getByRole("heading", { name: "AI batch intake" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Add manually instead" })).toHaveAttribute(
      "href",
      "/items/new",
    )
    expect(screen.getByRole("link", { name: "Items" })).toHaveAttribute("href", "/items")
    expect(screen.getByTestId("drafts-client")).toBeInTheDocument()
  })
})
