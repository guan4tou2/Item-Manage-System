import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import messages from "@/messages/zh-TW.json"

const pushMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/dashboard",
}))

import { MobileNav } from "./mobile-nav"

describe("MobileNav", () => {
  beforeEach(() => pushMock.mockReset())

  it("opens drawer and renders all nav labels", async () => {
    const user = userEvent.setup()
    render(
      <NextIntlClientProvider locale="zh-TW" messages={messages}>
        <MobileNav />
      </NextIntlClientProvider>,
    )
    await user.click(screen.getByRole("button", { name: /開啟選單/ }))
    expect(await screen.findByText("儀表板")).toBeInTheDocument()
    expect(screen.getByText("物品")).toBeInTheDocument()
    expect(screen.getByText("清單")).toBeInTheDocument()
    expect(screen.getByText("設定")).toBeInTheDocument()
  })

  it("clicking a nav item navigates and closes drawer", async () => {
    const user = userEvent.setup()
    render(
      <NextIntlClientProvider locale="zh-TW" messages={messages}>
        <MobileNav />
      </NextIntlClientProvider>,
    )
    await user.click(screen.getByRole("button", { name: /開啟選單/ }))
    await user.click(screen.getByText("物品"))
    expect(pushMock).toHaveBeenCalledWith("/items")
  })
})
