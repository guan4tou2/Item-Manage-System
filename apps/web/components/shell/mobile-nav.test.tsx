import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import messages from "@/messages/zh-TW.json"

const pushMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/dashboard",
}))

import { MobileNav } from "./mobile-nav"

function renderNav() {
  return render(
    <NextIntlClientProvider locale="zh-TW" messages={messages}>
      <MobileNav />
    </NextIntlClientProvider>,
  )
}

async function openDrawer(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /開啟選單/ }))
}

describe("MobileNav", () => {
  beforeEach(() => pushMock.mockReset())
  afterEach(() => vi.restoreAllMocks())

  it("groups the entries under four labelled sections", async () => {
    const user = userEvent.setup()
    renderNav()
    await openDrawer(user)

    const labels = messages.nav.groups
    expect(screen.getByTestId("nav-group-header-inventory")).toHaveTextContent(
      labels.inventory,
    )
    expect(screen.getByTestId("nav-group-header-analysis")).toHaveTextContent(
      labels.analysis,
    )
    expect(screen.getByTestId("nav-group-header-collab")).toHaveTextContent(
      labels.collab,
    )
    expect(screen.getByTestId("nav-group-header-system")).toHaveTextContent(
      labels.system,
    )
  })

  it("expands every group by default", async () => {
    const user = userEvent.setup()
    renderNav()
    await openDrawer(user)

    const inventory = screen.getByTestId("nav-group-items-inventory")
    expect(within(inventory).getByText(messages.nav.dashboard)).toBeInTheDocument()
    expect(within(inventory).getByText(messages.nav.items)).toBeInTheDocument()
    expect(within(inventory).getByText(messages.nav.scan)).toBeInTheDocument()
    expect(within(inventory).getByText(messages.nav.stocktakes)).toBeInTheDocument()
    expect(within(inventory).getByText(messages.nav.categories)).toBeInTheDocument()
    expect(within(inventory).getByText(messages.nav.locations)).toBeInTheDocument()

    expect(screen.getByTestId("nav-group-header-inventory")).toHaveAttribute(
      "aria-expanded",
      "true",
    )
    expect(
      within(screen.getByTestId("nav-group-items-analysis")).getByText(
        messages.nav.reports,
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByTestId("nav-group-items-collab")).getByText(
        messages.nav.lists,
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByTestId("nav-group-items-system")).getByText(
        messages.nav.settings,
      ),
    ).toBeInTheDocument()
  })

  it("collapses and re-expands a group when its header is clicked", async () => {
    const user = userEvent.setup()
    renderNav()
    await openDrawer(user)

    const header = screen.getByTestId("nav-group-header-analysis")
    await user.click(header)
    expect(header).toHaveAttribute("aria-expanded", "false")
    expect(screen.queryByTestId("nav-group-items-analysis")).not.toBeInTheDocument()

    await user.click(header)
    expect(header).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByTestId("nav-group-items-analysis")).toBeInTheDocument()
  })

  it("navigates to reports and closes the drawer", async () => {
    const user = userEvent.setup()
    renderNav()
    await openDrawer(user)

    await user.click(
      within(screen.getByTestId("nav-group-items-analysis")).getByText(
        messages.nav.reports,
      ),
    )

    expect(pushMock).toHaveBeenCalledWith("/reports")
  })

  it("navigates to items from its group", async () => {
    const user = userEvent.setup()
    renderNav()
    await openDrawer(user)

    await user.click(
      within(screen.getByTestId("nav-group-items-inventory")).getByText(
        messages.nav.items,
      ),
    )

    expect(pushMock).toHaveBeenCalledWith("/items")
  })

  it("does not emit dialog description warnings", async () => {
    const user = userEvent.setup()
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {})

    renderNav()
    await openDrawer(user)

    const output = [...warnSpy.mock.calls, ...errorSpy.mock.calls]
      .flat()
      .join(" ")
    expect(output).not.toContain("Missing `Description`")
  })

  it("uses a localized label for the close button", async () => {
    const user = userEvent.setup()
    renderNav()

    await openDrawer(user)

    expect(screen.getByRole("button", { name: "關閉選單" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument()
  })
})
