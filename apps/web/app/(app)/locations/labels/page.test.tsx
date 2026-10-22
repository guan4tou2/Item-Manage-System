import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as locationLabelsApi from "@/lib/api/location-labels"
import * as locationsApi from "@/lib/api/locations"
import enMessages from "@/messages/en.json"

import LocationLabelsPage from "./page"

const searchParams = new URLSearchParams("ids=8&ids=9")

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/location-labels", () => ({
  getBulkLocationLabelBundles: vi.fn(),
}))

vi.mock("@/lib/api/locations", () => ({
  listLocations: vi.fn(),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <LocationLabelsPage />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("LocationLabelsPage", () => {
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
    vi.mocked(locationLabelsApi.getBulkLocationLabelBundles).mockResolvedValue({
      labels: [
        {
          locationId: 8,
          label: {
            location_id: 8,
            name: "藥箱",
            path: "1F / 廚房 / 藥箱",
            item_count: 12,
            deep_link: "https://example.test/items?location=8",
          },
          qrBlob: new Blob(["png"], { type: "image/png" }),
        },
      ],
      skippedCount: 1,
    })
    vi.mocked(locationsApi.listLocations).mockResolvedValue([
      { id: 8, name: "藥箱", path: "1F / 廚房 / 藥箱" },
      { id: 9, name: "冰箱", path: "1F / 廚房 / 冰箱" },
    ] as never)
  })

  it("以 ids 參數直接產生標籤卡（QR、名稱、路徑、物品數）", async () => {
    renderPage()

    expect(await screen.findByText("藥箱")).toBeInTheDocument()
    expect(screen.getByText("1F / 廚房 / 藥箱")).toBeInTheDocument()
    expect(screen.getByText("12 items")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to locations" })).toHaveAttribute(
      "href",
      "/locations",
    )

    await waitFor(() => {
      expect(locationLabelsApi.getBulkLocationLabelBundles).toHaveBeenCalledWith(
        [8, 9],
        "jwt",
      )
    })
  })

  it("顯示略過的位置數", async () => {
    renderPage()
    expect(await screen.findByText("1 label skipped")).toBeInTheDocument()
  })

  it("無 ids 時列出位置供勾選，勾選後產生標籤", async () => {
    searchParams.delete("ids")
    renderPage()

    const checkbox = await screen.findByRole("checkbox", { name: /藥箱/ })
    expect(checkbox).toBeInTheDocument()

    expect(screen.getByText("冰箱")).toBeInTheDocument()
    expect(locationLabelsApi.getBulkLocationLabelBundles).not.toHaveBeenCalled()
  })
})
