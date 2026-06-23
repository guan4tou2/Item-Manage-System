import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
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
})
