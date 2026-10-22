import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as labelsApi from "@/lib/api/labels"
import enMessages from "@/messages/en.json"

import BulkItemLabelsPage from "./page"

const searchParams = new URLSearchParams("ids=item-1&ids=missing")

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/labels", () => ({
  getBulkItemLabelBundles: vi.fn(),
  getItemLabelsPdf: vi.fn(),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <BulkItemLabelsPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("BulkItemLabelsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:qr"),
    })
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    })
    vi.mocked(labelsApi.getBulkItemLabelBundles).mockResolvedValue({
      items: [
        {
          itemId: "item-1",
          label: {
            item_id: "item-1",
            name: "Router",
            quantity: 2,
            deep_link: "https://example.test/items/item-1",
            barcode: "4710085200016",
          },
          qrBlob: new Blob(["png"], { type: "image/png" }),
        },
      ],
      skippedCount: 1,
    })
  })

  it("renders printable labels and skipped item feedback", async () => {
    renderPage()

    expect(await screen.findByText("Router")).toBeInTheDocument()
    expect(screen.getByText("4710085200016")).toBeInTheDocument()
    expect(screen.getByText("1 label skipped")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to items" })).toHaveAttribute("href", "/items")

    await waitFor(() => {
      expect(labelsApi.getBulkItemLabelBundles).toHaveBeenCalledWith(
        ["item-1", "missing"],
        "jwt",
      )
    })
  })

  it("prints a Code128 barcode image on each label (Phase 37)", async () => {
    renderPage()

    const holder = await screen.findByTestId("label-barcode")
    await waitFor(() => expect(holder.querySelector("svg")).not.toBeNull())
  })

  it("downloads the server-side label PDF (Phase 41)", async () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {})
    vi.mocked(labelsApi.getItemLabelsPdf).mockResolvedValue({
      blob: new Blob(["%PDF"], { type: "application/pdf" }),
      filename: "item-labels-20261023.pdf",
    })
    renderPage()

    await screen.findByText("Router")
    fireEvent.click(screen.getByRole("button", { name: "Download PDF" }))

    await waitFor(() => {
      expect(labelsApi.getItemLabelsPdf).toHaveBeenCalledWith(
        ["item-1", "missing"],
        "jwt",
      )
    })
    expect(click).toHaveBeenCalled()
  })

  it("shows an error when the PDF download fails (Phase 41)", async () => {
    vi.mocked(labelsApi.getItemLabelsPdf).mockRejectedValue(new Error("boom"))
    renderPage()

    await screen.findByText("Router")
    fireEvent.click(screen.getByRole("button", { name: "Download PDF" }))

    expect(
      await screen.findByText("Failed to download the PDF. Please try again."),
    ).toBeInTheDocument()
  })
})
