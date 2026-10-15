import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"

import { ExpiryBadge, daysUntil, taipeiTodayIso } from "./expiry-badge"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

function iso(offsetDays: number): string {
  const base = Date.parse(`${taipeiTodayIso()}T00:00:00Z`)
  return new Date(base + offsetDays * 86_400_000).toISOString().slice(0, 10)
}

describe("ExpiryBadge", () => {
  it("labels each state with text and the §5.6 token classes", () => {
    const { rerender } = render(<ExpiryBadge date={iso(-3)} />, { wrapper: Provider })

    const expired = screen.getByText("Expired 3d")
    expect(expired).toHaveAttribute("data-status", "expired")
    expect(expired.className).toContain("text-destructive")

    rerender(<ExpiryBadge date={iso(2)} />)
    const expiring = screen.getByText("2d left")
    expect(expiring).toHaveAttribute("data-status", "expiring")
    expect(expiring.className).toContain("text-warning")

    rerender(<ExpiryBadge date={iso(0)} />)
    expect(screen.getByText("Expires today")).toHaveAttribute("data-status", "expiring")

    rerender(<ExpiryBadge date={iso(30)} />)
    const ok = screen.getByText(iso(30))
    expect(ok).toHaveAttribute("data-status", "ok")
    expect(ok.className).toContain("text-muted-foreground")
  })

  it("omits the badge for far dates when fallback is none", () => {
    const { container } = render(<ExpiryBadge date={iso(30)} fallback="none" />, {
      wrapper: Provider,
    })

    expect(container).toBeEmptyDOMElement()
  })

  it("computes days against the Taipei calendar day", () => {
    expect(daysUntil(iso(0))).toBe(0)
    expect(daysUntil(iso(-5))).toBe(-5)
    expect(daysUntil(iso(6))).toBe(6)

    const late = new Date("2026-06-19T15:59:00Z") // 台北 6/19 23:59
    expect(taipeiTodayIso(late)).toBe("2026-06-19")
    const midnight = new Date("2026-06-19T16:00:00Z") // 台北 6/20 00:00
    expect(taipeiTodayIso(midnight)).toBe("2026-06-20")
    expect(daysUntil("2026-06-20", late)).toBe(1)
    expect(daysUntil("2026-06-20", midnight)).toBe(0)
  })
})
