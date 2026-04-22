import { renderHook, act } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"

const setNextTheme = vi.fn()
const mutate = vi.fn()

vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: undefined, setTheme: setNextTheme }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: vi.fn(),
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  useUpdatePreferences: () => ({ mutate, isPending: false }),
  usePreferences: () => ({ data: undefined, isSuccess: false }),
}))

import { useAccessToken } from "@/lib/auth/use-auth"
import { useThemePreference } from "./use-theme"

describe("useThemePreference", () => {
  beforeEach(() => {
    setNextTheme.mockClear()
    mutate.mockClear()
  })

  it("returns system as default when next-themes theme is undefined", () => {
    vi.mocked(useAccessToken).mockReturnValue(null)
    const { result } = renderHook(() => useThemePreference())
    expect(result.current.theme).toBe("system")
  })

  it("calls next-themes setTheme but skips mutation when not authenticated", () => {
    vi.mocked(useAccessToken).mockReturnValue(null)
    const { result } = renderHook(() => useThemePreference())
    act(() => result.current.setTheme("dark"))
    expect(setNextTheme).toHaveBeenCalledWith("dark")
    expect(mutate).not.toHaveBeenCalled()
  })

  it("calls both next-themes setTheme and mutation when authenticated", () => {
    vi.mocked(useAccessToken).mockReturnValue("token-abc")
    const { result } = renderHook(() => useThemePreference())
    act(() => result.current.setTheme("light"))
    expect(setNextTheme).toHaveBeenCalledWith("light")
    expect(mutate).toHaveBeenCalledWith({ theme: "light" })
  })
})
