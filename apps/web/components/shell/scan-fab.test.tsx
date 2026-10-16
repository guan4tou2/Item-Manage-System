import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import { ScanFab } from "./scan-fab"

const navMocks = vi.hoisted(() => ({ pathname: "/items" }))
vi.mock("next/navigation", () => ({ usePathname: () => navMocks.pathname }))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

beforeEach(() => {
  navMocks.pathname = "/items"
})

describe("ScanFab", () => {
  it("renders a mobile-only link to the scan page with an accessible name", () => {
    render(<ScanFab />, { wrapper: Provider })

    const link = screen.getByRole("link", { name: "Scan barcode" })
    expect(link).toHaveAttribute("href", "/scan")
    expect(link.className).toContain("md:hidden")
    expect(link.className).toContain("safe-area-inset-bottom")
  })

  it("stays clear of the bottom edge on devices with a safe area", () => {
    render(<ScanFab />, { wrapper: Provider })

    expect(screen.getByRole("link", { name: "Scan barcode" }).className).toContain(
      "bottom-[calc(1rem+env(safe-area-inset-bottom))]",
    )
  })

  it("hides itself on the scan page", () => {
    navMocks.pathname = "/scan"

    render(<ScanFab />, { wrapper: Provider })

    expect(screen.queryByRole("link", { name: "Scan barcode" })).toBeNull()
  })
})
