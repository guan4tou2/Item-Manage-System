import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import type { BarcodeLocalMatch } from "@/lib/api/barcodes"

import { BarcodeCandidates } from "./barcode-candidates"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/client")>()),
  apiFetch: vi.fn(async () => ({
    ok: true,
    status: 200,
    blob: async () => new Blob(["png"], { type: "image/png" }),
  })),
}))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const matches: BarcodeLocalMatch[] = [
  {
    id: "item-1",
    name: "Milk",
    quantity: 2,
    image_id: "img-1",
    location_path: "1F / Kitchen / Top shelf",
  },
  {
    id: "item-2",
    name: "Milk (spare)",
    quantity: 1,
    image_id: null,
    location_path: null,
  },
]

describe("BarcodeCandidates", () => {
  it("renders count, names, location paths, quantities, and thumbnails", async () => {
    render(<BarcodeCandidates matches={matches} />, { wrapper: Provider })

    expect(screen.getByText("2 matching items")).toBeInTheDocument()
    expect(screen.getByText("Milk")).toBeInTheDocument()
    expect(screen.getByText("1F / Kitchen / Top shelf")).toBeInTheDocument()
    expect(screen.getByText("Qty 2")).toBeInTheDocument()
    expect(screen.getByText("Qty 1")).toBeInTheDocument()
    // 縮圖需 Bearer：經 AuthImage 轉 object URL 呈現
    expect(await screen.findByAltText("")).toHaveAttribute("src", "blob:mock")
    // 無位置 → fallback 文案
    expect(screen.getByText("No location set")).toBeInTheDocument()
  })

  it("links each candidate to the item page", () => {
    render(<BarcodeCandidates matches={matches} />, { wrapper: Provider })

    const links = screen.getAllByRole("link")
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/items/item-1",
      "/items/item-2",
    ])
  })

  it("renders nothing for an empty match list", () => {
    const { container } = render(<BarcodeCandidates matches={[]} />, {
      wrapper: Provider,
    })

    expect(container.querySelector('[data-testid="barcode-candidates"]')).toBeNull()
  })
})
