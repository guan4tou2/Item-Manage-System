import { act, fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { InstallPwaButton } from "./install-pwa-button"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

describe("InstallPwaButton", () => {
  it("renders nothing when no beforeinstallprompt event", () => {
    const { container } = render(<InstallPwaButton />, { wrapper: Provider })
    expect(container).toBeEmptyDOMElement()
  })

  it("appears when beforeinstallprompt fires and calls prompt on click", async () => {
    render(<InstallPwaButton />, { wrapper: Provider })
    const prompt = vi.fn().mockResolvedValue(undefined)
    const evt = new Event("beforeinstallprompt")
    Object.assign(evt, { prompt, userChoice: Promise.resolve({ outcome: "dismissed" }) })
    await act(async () => {
      window.dispatchEvent(evt)
    })
    const btn = await screen.findByRole("button", { name: /install/i })
    fireEvent.click(btn)
    expect(prompt).toHaveBeenCalled()
  })
})
