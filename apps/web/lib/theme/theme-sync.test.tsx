import { render, cleanup } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const setTheme = vi.fn()

vi.mock("next-themes", () => ({
  useTheme: () => ({ setTheme }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: vi.fn(),
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: vi.fn(),
}))

import { useAccessToken } from "@/lib/auth/use-auth"
import { usePreferences } from "@/lib/preferences/use-preferences"
import { ThemeSync } from "./theme-sync"

describe("ThemeSync", () => {
  beforeEach(() => {
    setTheme.mockClear()
  })
  afterEach(() => cleanup())

  it("no-ops when unauthenticated", () => {
    vi.mocked(useAccessToken).mockReturnValue(null)
    vi.mocked(usePreferences).mockReturnValue({
      data: undefined,
      isSuccess: false,
    } as never)
    render(<ThemeSync />)
    expect(setTheme).not.toHaveBeenCalled()
  })

  it("applies theme from API once when authenticated", () => {
    vi.mocked(useAccessToken).mockReturnValue("token-a")
    vi.mocked(usePreferences).mockReturnValue({
      data: { theme: "dark" },
      isSuccess: true,
    } as never)
    const { rerender } = render(<ThemeSync />)
    expect(setTheme).toHaveBeenCalledWith("dark")
    expect(setTheme).toHaveBeenCalledTimes(1)
    rerender(<ThemeSync />)
    expect(setTheme).toHaveBeenCalledTimes(1)
  })

  it("re-syncs when the access token changes", () => {
    vi.mocked(useAccessToken).mockReturnValue("token-a")
    vi.mocked(usePreferences).mockReturnValue({
      data: { theme: "dark" },
      isSuccess: true,
    } as never)
    const { rerender } = render(<ThemeSync />)
    expect(setTheme).toHaveBeenCalledWith("dark")

    // Simulate logout then login as different user with different theme
    vi.mocked(useAccessToken).mockReturnValue(null)
    vi.mocked(usePreferences).mockReturnValue({
      data: undefined,
      isSuccess: false,
    } as never)
    rerender(<ThemeSync />)

    vi.mocked(useAccessToken).mockReturnValue("token-b")
    vi.mocked(usePreferences).mockReturnValue({
      data: { theme: "light" },
      isSuccess: true,
    } as never)
    rerender(<ThemeSync />)

    expect(setTheme).toHaveBeenLastCalledWith("light")
    expect(setTheme).toHaveBeenCalledTimes(2)
  })
})
