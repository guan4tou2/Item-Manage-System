import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeAll, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { toast } from "sonner"

import { PreferencesForm } from "./preferences-form"

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn().mockResolvedValue({
    theme: "system",
    language: "zh-TW",
    currency: "TWD",
  }),
}))

vi.mock("@/lib/preferences/use-preferences", () => ({
  usePreferences: () => ({
    data: { theme: "system", language: "zh-TW", currency: "TWD" },
  }),
  useUpdatePreferences: () => ({ mutateAsync: mocks.mutateAsync }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn()
  Element.prototype.setPointerCapture = vi.fn()
  Element.prototype.releasePointerCapture = vi.fn()
})

const t = enMessages.settings.preferences

function renderForm() {
  render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <PreferencesForm />
    </NextIntlClientProvider>,
  )
}

describe("PreferencesForm", () => {
  it("renders theme, language, and currency pickers with the current values", () => {
    renderForm()

    expect(screen.getByText(t.theme)).toBeInTheDocument()
    expect(screen.getByText(t.language)).toBeInTheDocument()
    expect(screen.getByText(t.currency)).toBeInTheDocument()
    expect(screen.getAllByRole("combobox")).toHaveLength(3)
    expect(screen.getByText(enMessages.theme.system)).toBeInTheDocument()
    expect(screen.getByText(enMessages.locale["zh-TW"])).toBeInTheDocument()
    expect(screen.getByText(enMessages.currency.TWD)).toBeInTheDocument()
  })

  it("shows a live amount preview using the account currency", () => {
    renderForm()

    expect(screen.getByTestId("currency-preview")).toHaveTextContent("NT$1,200")
  })

  it("updates the currency through the mutation", async () => {
    const user = userEvent.setup()
    renderForm()

    await user.click(screen.getAllByRole("combobox")[2]!)
    await user.click(
      await screen.findByRole("option", { name: enMessages.currency.JPY }),
    )

    expect(mocks.mutateAsync).toHaveBeenCalledWith({ currency: "JPY" })
  })
})

describe("PreferencesForm — AI 資料分享（Phase 34）", () => {
  it("renders the AI data sharing toggle, off by default", () => {
    renderForm()

    expect(screen.getByText(t.aiSharing)).toBeInTheDocument()
    expect(screen.getByText(t.aiSharingHint)).toBeInTheDocument()
    expect(screen.getByRole("switch")).not.toBeChecked()
  })

  it("enables AI data sharing and confirms with a toast", async () => {
    const user = userEvent.setup()
    renderForm()

    await user.click(screen.getByRole("switch"))

    expect(mocks.mutateAsync).toHaveBeenCalledWith({ ai_data_sharing_enabled: true })
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith(t.aiSharingOn))
  })

  it("reports a failure when the update fails", async () => {
    const user = userEvent.setup()
    mocks.mutateAsync.mockRejectedValueOnce(new Error("boom"))
    renderForm()

    await user.click(screen.getByRole("switch"))

    await waitFor(() =>
      expect(screen.getByRole("switch")).not.toBeChecked(),
    )
  })
})
