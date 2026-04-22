import { render } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

let tokenRef: string | null = "jwt-1"
let prefsData: { language?: string } | undefined = { language: "en" }
let prefsSuccess = true

const refreshMock = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock }),
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => tokenRef,
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: () => ({ data: prefsData, isSuccess: prefsSuccess }),
}))

import { LocaleSync } from "./locale-sync"

function renderWith(locale: "zh-TW" | "en") {
  return render(
    <NextIntlClientProvider locale={locale} messages={{}}>
      <LocaleSync />
    </NextIntlClientProvider>,
  )
}

describe("LocaleSync", () => {
  beforeEach(() => {
    refreshMock.mockReset()
    document.cookie = "ims_locale=; Path=/; Max-Age=0"
    tokenRef = "jwt-1"
    prefsData = { language: "en" }
    prefsSuccess = true
  })

  it("writes cookie and refreshes when server language differs from current locale", () => {
    renderWith("zh-TW")
    expect(document.cookie).toContain("ims_locale=en")
    expect(refreshMock).toHaveBeenCalled()
  })

  it("does not refresh when server language equals current locale", () => {
    prefsData = { language: "zh-TW" }
    renderWith("zh-TW")
    expect(refreshMock).not.toHaveBeenCalled()
  })

  it("does nothing when token is null", () => {
    tokenRef = null
    renderWith("zh-TW")
    expect(refreshMock).not.toHaveBeenCalled()
  })
})
