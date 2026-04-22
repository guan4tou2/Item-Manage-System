import { renderHook, act } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const refreshMock = vi.fn()
const mutateMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock }),
}))

vi.mock("next-intl", () => ({
  useLocale: () => "zh-TW",
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt-abc",
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  useUpdatePreferences: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}))

import { useLocale } from "./use-locale"

describe("useLocale", () => {
  beforeEach(() => {
    refreshMock.mockReset()
    mutateMock.mockReset()
    document.cookie = "ims_locale=; Path=/; Max-Age=0"
  })

  it("returns current locale", () => {
    const { result } = renderHook(() => useLocale())
    expect(result.current.locale).toBe("zh-TW")
  })

  it("setLocale writes cookie, calls mutate, and refreshes", () => {
    const { result } = renderHook(() => useLocale())
    act(() => result.current.setLocale("en"))
    expect(document.cookie).toContain("ims_locale=en")
    expect(mutateMock).toHaveBeenCalledWith({ language: "en" })
    expect(refreshMock).toHaveBeenCalled()
  })
})
