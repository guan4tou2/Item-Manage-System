import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

// next-intl requires nested message objects; convert flat zh-TW keys to nested structure
import flatMessages from "@/messages/zh-TW.json"

type NestedMessages = Record<string, Record<string, string>>
const messages: NestedMessages = Object.entries(flatMessages).reduce(
  (acc, [key, value]) => {
    const [ns, ...rest] = key.split(".")
    if (!ns) return acc
    if (!acc[ns]) acc[ns] = {}
    acc[ns][rest.join(".")] = value
    return acc
  },
  {} as NestedMessages,
)

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
