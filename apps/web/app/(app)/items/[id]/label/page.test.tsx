import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"

import ItemLabelPage from "./page"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "item-1" }),
}))

const labelState = vi.hoisted(() => ({
  data: null as null | {
    item_id: string
    name: string
    quantity: number
    deep_link: string
    barcode: string | null
  },
}))

vi.mock("@/lib/hooks/use-label", () => ({
  useItemLabel: () => ({ data: labelState.data, isLoading: false, isError: false }),
  useItemQrObjectUrl: () => "blob:qr",
}))

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

beforeEach(() => {
  labelState.data = {
    item_id: "item-1",
    name: "Camera",
    quantity: 3,
    deep_link: "https://example.test/items/item-1",
    barcode: "4710085200016",
  }
})

describe("ItemLabelPage", () => {
  it("prints the barcode digits under the QR label", () => {
    render(<ItemLabelPage />, { wrapper: Provider })

    expect(screen.getByText("Camera")).toBeInTheDocument()
    expect(screen.getByText("4710085200016")).toBeInTheDocument()
    expect(screen.getByRole("img", { name: "QR code for Camera" })).toBeInTheDocument()
  })

  it("omits the barcode line when the item has none", () => {
    labelState.data = { ...labelState.data!, barcode: null }

    render(<ItemLabelPage />, { wrapper: Provider })

    expect(screen.getByText("Camera")).toBeInTheDocument()
    expect(screen.queryByText("4710085200016")).toBeNull()
  })
})
