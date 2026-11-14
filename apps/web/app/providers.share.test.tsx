import { render, screen } from "@testing-library/react"
import { beforeEach, expect, it, vi } from "vitest"

import { Providers } from "./providers"

const { path, sync } = vi.hoisted(() => ({ path: { value: "/share" }, sync: vi.fn() }))
vi.mock("next/navigation", () => ({ usePathname: () => path.value }))
vi.mock("next-themes", () => ({ ThemeProvider: ({ children }: { children: React.ReactNode }) => children }))
vi.mock("@/lib/auth/cookie-sync", () => ({ useTokenCookieSync: sync }))
vi.mock("@/lib/theme/theme-sync", () => ({ ThemeSync: () => { sync("theme"); return null } }))
vi.mock("@/lib/locale/locale-sync", () => ({ LocaleSync: () => { sync("locale"); return null } }))
vi.mock("@/components/ui/sonner", () => ({ Toaster: () => null }))
beforeEach(() => { sync.mockClear(); path.value = "/share" })

it("公開頁略過所有可能發出登入請求的同步元件", () => {
  render(<Providers><p>Shared content</p></Providers>)
  expect(screen.getByText("Shared content")).toBeVisible()
  expect(sync).not.toHaveBeenCalled()
})
it("應用程式其他頁面保留既有同步", () => {
  path.value = "/lists"
  render(<Providers><p>Lists</p></Providers>)
  expect(sync).toHaveBeenCalledWith("theme")
  expect(sync).toHaveBeenCalledWith("locale")
})
