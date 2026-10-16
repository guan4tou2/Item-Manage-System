import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { PreferencesForm } from "./preferences-form"

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: () => ({ data: { theme: "system", language: "zh-TW" } }),
  useUpdatePreferences: () => ({ mutateAsync: vi.fn() }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.preferences

describe("PreferencesForm", () => {
  it("renders theme and language pickers with the current values", () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <PreferencesForm />
      </NextIntlClientProvider>,
    )

    expect(screen.getByText(t.theme)).toBeInTheDocument()
    expect(screen.getByText(t.language)).toBeInTheDocument()
    expect(screen.getAllByRole("combobox")).toHaveLength(2)
    expect(screen.getByText(enMessages.theme.system)).toBeInTheDocument()
    expect(screen.getByText(enMessages.locale["zh-TW"])).toBeInTheDocument()
  })
})
