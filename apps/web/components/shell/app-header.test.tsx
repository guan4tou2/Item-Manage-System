import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import messages from "@/messages/zh-TW.json"

const mocks = vi.hoisted(() => ({ pathname: "/dashboard" }))

vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
}))

vi.mock("./mobile-nav", () => ({
  MobileNav: () => <div data-testid="mobile-nav" />,
}))

vi.mock("./notification-bell", () => ({
  NotificationBell: () => <div data-testid="notification-bell" />,
}))

vi.mock("./user-menu", () => ({
  UserMenu: () => <div data-testid="user-menu" />,
}))

vi.mock("@/components/pwa/install-pwa-button", () => ({
  InstallPwaButton: () => null,
}))

import { AppHeader } from "./app-header"

function renderHeader() {
  return render(
    <NextIntlClientProvider locale="zh-TW" messages={messages}>
      <AppHeader />
    </NextIntlClientProvider>,
  )
}

describe("AppHeader", () => {
  beforeEach(() => {
    mocks.pathname = "/dashboard"
  })

  it("keeps ten first-level links plus the statistics menu trigger", () => {
    renderHeader()

    const nav = screen.getByRole("navigation")
    expect(within(nav).getAllByRole("link")).toHaveLength(10)
    expect(
      within(nav).getByRole("button", { name: messages.nav.statistics }),
    ).toBeInTheDocument()
  })

  it("opens the statistics menu with links to statistics and reports", async () => {
    const user = userEvent.setup()
    renderHeader()

    await user.click(
      screen.getByRole("button", { name: messages.nav.statistics }),
    )

    expect(
      screen.getByRole("menuitem", { name: messages.nav.statistics }),
    ).toHaveAttribute("href", "/statistics")
    expect(
      screen.getByRole("menuitem", { name: messages.nav.reports }),
    ).toHaveAttribute("href", "/reports")
  })

  it("marks the statistics trigger active on /reports", () => {
    mocks.pathname = "/reports"
    renderHeader()

    expect(
      screen.getByRole("button", { name: messages.nav.statistics }),
    ).toHaveClass("bg-accent")
  })

  it("marks the statistics trigger active on /statistics", () => {
    mocks.pathname = "/statistics"
    renderHeader()

    expect(
      screen.getByRole("button", { name: messages.nav.statistics }),
    ).toHaveClass("bg-accent")
  })

  it("leaves the statistics trigger inactive elsewhere", () => {
    mocks.pathname = "/items"
    renderHeader()

    expect(
      screen.getByRole("button", { name: messages.nav.statistics }),
    ).not.toHaveClass("bg-accent")
  })
})
