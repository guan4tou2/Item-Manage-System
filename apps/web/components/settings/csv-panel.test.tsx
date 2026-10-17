import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { toast } from "sonner"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as api from "@/lib/api/items-bulk"
import enMessages from "@/messages/en.json"

import { CsvPanel } from "./csv-panel"

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/items-bulk", () => ({
  downloadItemsCsv: vi.fn(),
  importItemsCsv: vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const t = enMessages.settings.csv

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <CsvPanel />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("CsvPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.downloadItemsCsv).mockResolvedValue(undefined)
    vi.mocked(api.importItemsCsv).mockResolvedValue({
      total_rows: 2,
      created_count: 2,
      errors: [],
    } as never)
  })

  it("downloads the csv export", async () => {
    renderPanel()

    fireEvent.click(screen.getByRole("button", { name: t.downloadCsv }))

    await waitFor(() => {
      expect(vi.mocked(api.downloadItemsCsv)).toHaveBeenCalledWith("jwt")
    })
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith(t.toast.exportDone)
  })

  it("imports a csv file and shows the summary", async () => {
    const { container } = renderPanel()

    const file = new File(["name\n"], "items.csv", { type: "text/csv" })
    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(vi.mocked(api.importItemsCsv)).toHaveBeenCalledWith(file, "jwt")
    })
    // 匯入摘要：total_rows=2、created_count=2 以 strong 節點呈現（直文本節點為標籤）。
    expect(await screen.findAllByText("2", { selector: "strong" })).toHaveLength(2)
    // toast 由 next-intl 內插 count 後以單一引數呼叫。
    expect(vi.mocked(toast.success)).toHaveBeenCalledTimes(1)
  })

  it("documents the cost and currency columns (matches EXPORT_COLUMNS)", () => {
    renderPanel()

    // 欄位清單：min_quantity 後緊接 cost、currency
    expect(screen.getByText(/id, name, description, barcode/)).toHaveTextContent(
      "quantity, min_quantity, cost, currency, category_name",
    )
    // 匯入說明需提及 cost（最多 2 位小數）與 currency（帳號幣別）
    expect(screen.getByText(/cost \(up to 2 decimals\)/)).toBeInTheDocument()
    expect(screen.getByText(/currency \(must match your account currency\)/)).toBeInTheDocument()
  })
})
