import { render, screen, within, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { offlineQueue } from "@/lib/offline/runtime"
import messages from "@/messages/zh-TW.json"

const pushMock = vi.fn()
const logoutMutateMock = vi.fn()
const setLocaleMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useCurrentUser: () => ({ email: "me@example.com", username: "me", id: 1 }),
  useLogout: () => ({ mutateAsync: logoutMutateMock, isPending: false }),
}))

vi.mock("@/lib/locale/use-locale", () => ({
  useLocale: () => ({ locale: "zh-TW", setLocale: setLocaleMock, isSyncing: false }),
}))

vi.mock("@/lib/theme/use-theme", () => ({
  useThemePreference: () => ({
    theme: "system",
    setTheme: vi.fn(),
    isSyncing: false,
  }),
}))

import { UserMenu } from "./user-menu"

function renderWithIntl(ui: React.ReactElement) {
  return render(
    <NextIntlClientProvider locale="zh-TW" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  )
}

describe("UserMenu", () => {
  beforeEach(() => {
    pushMock.mockReset()
    logoutMutateMock.mockReset().mockResolvedValue(undefined)
    setLocaleMock.mockReset()
  })

  it("opens and shows email + menu items", async () => {
    const user = userEvent.setup()
    renderWithIntl(<UserMenu />)
    await user.click(screen.getByRole("button", { name: /使用者選單/ }))
    expect(screen.getByText("me@example.com")).toBeInTheDocument()
    expect(screen.getByText("個人設定")).toBeInTheDocument()
    expect(screen.getByText("登出")).toBeInTheDocument()
  })

  it("clicking logout triggers mutateAsync then redirects to /login", async () => {
    const user = userEvent.setup()
    renderWithIntl(<UserMenu />)
    await user.click(screen.getByRole("button", { name: /使用者選單/ }))
    await user.click(screen.getByText("登出"))
    expect(logoutMutateMock).toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith("/login")
  })
})


describe("UserMenu 離線佇列登出提示", () => {
  afterEach(() => vi.restoreAllMocks())

  it("有待同步項目先確認，取消不登出；確認後也不刪除紀錄", async () => {
    const list = vi.spyOn(offlineQueue.storage, "list").mockResolvedValue([{ client_id: "pending" } as never])
    const remove = vi.spyOn(offlineQueue.storage, "remove").mockResolvedValue()
    logoutMutateMock.mockClear()
    const user = userEvent.setup()
    renderWithIntl(<UserMenu />)
    await user.click(screen.getByRole("button", { name: /使用者選單/ }))
    await user.click(screen.getByText("登出"))
    const dialog = await screen.findByRole("alertdialog")
    expect(list).toHaveBeenCalledWith(1)
    expect(within(dialog).getByText(messages.offline.logoutWarning)).toBeInTheDocument()
    expect(logoutMutateMock).not.toHaveBeenCalled()
    await user.click(within(dialog).getByRole("button", { name: "取消" }))
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument())
    expect(logoutMutateMock).not.toHaveBeenCalled()
    await user.click(screen.getByRole("button", { name: /使用者選單/ }))
    await user.click(screen.getByText("登出"))
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "登出" }))
    await waitFor(() => expect(logoutMutateMock).toHaveBeenCalledTimes(1))
    expect(remove).not.toHaveBeenCalled()
  })
})
