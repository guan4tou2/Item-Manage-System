import { fireEvent, render, screen, within } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { ReactNode } from "react"

import type { ReceiptRead } from "@/lib/api/ai-receipts"
import { ApiError } from "@/lib/api/client"
import en from "@/messages/en.json"
import { ReceiptDetail } from "./receipt-detail"

const state = vi.hoisted(() => ({ readOnly: false, query: {} as Record<string, unknown>, refetch: vi.fn() }))
vi.mock("@/lib/auth/use-readonly", () => ({ useReadOnly: () => state.readOnly }))
vi.mock("@/lib/hooks/use-ai-receipts", () => ({ useReceipt: () => state.query }))
vi.mock("./receipt-review-actions", () => ({ ReceiptReviewActions: () => <button>review action</button> }))
vi.mock("@/components/common/auth-image", () => ({ AuthImage: ({ fallback }: { fallback: ReactNode }) => fallback }))
function detail(): ReceiptRead {
  return {
    receipt_id: "r1", review: null, image_id: "image-1",
    snapshot: { merchant: "商店", purchased_at: "2026-11-14", currency: "XXX", page_count: 2,
      total: "30", item_total: "30", discrepancy: "0", truncated: false, balance_status: "balanced", calculated_total: "30" },
    lines: [
      { draft_id: "a", index: 0, name: "紙本名稱", quantity: 3, unit_price: "10", subtotal: "30", status: "accepted", item_id: "item-1" },
      { draft_id: "b", index: 1, name: "已刪物品", status: "accepted", item_id: null },
      { draft_id: "c", index: 2, name: "待確認品項", status: "ready" },
      { draft_id: "d", index: 3, name: "捨棄品項", status: "discarded" },
      { draft_id: "e", index: 4, name: "失敗品項", status: "failed" },
    ],
  }
}
function mount() {
  return render(<NextIntlClientProvider locale="en" messages={en}><ReceiptDetail receiptId="r1" /></NextIntlClientProvider>)
}
beforeEach(() => {
  state.readOnly = false
  state.refetch.mockReset()
  state.query = { data: detail(), isPending: false, isError: false, refetch: state.refetch }
})
describe("整張收據", () => {
  it("載入時有 skeleton 與返回入口", () => {
    state.query = { isPending: true }
    mount()
    expect(screen.getByLabelText("Entire receipt")).toHaveAttribute("aria-busy", "true")
    expect(screen.getByRole("link", { name: "Back to draft queue" })).toBeInTheDocument()
  })
  it("404 顯示找不到，不提供無效重試", () => {
    state.query = { isError: true, error: new ApiError(404, {}) }
    mount()
    expect(screen.getByRole("alert")).toHaveTextContent("Receipt not found")
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to draft queue" })).toBeInTheDocument()
  })
  it("其他錯誤可重試", () => {
    state.query = { isError: true, error: new Error("離線"), refetch: state.refetch }
    mount()
    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    expect(state.refetch).toHaveBeenCalledOnce()
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load")
  })
  it.each([true, false])("viewer 與伺服器 403 使用唯讀說明：角色=%s", (readOnly) => {
    state.readOnly = readOnly
    if (!readOnly) state.query = { isError: true, error: new ApiError(403, {}) }
    mount()
    expect(screen.getByTestId("viewer-notice")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "review action" })).not.toBeInTheDocument()
  })
  it("桌面與手機呈現所有狀態，已刪物品無連結；影像失敗保留資料", () => {
    mount()
    const table = within(screen.getByRole("table"))
    expect(table.getByRole("link", { name: "紙本名稱" })).toHaveAttribute("href", "/items/item-1")
    expect(table.queryByRole("link", { name: "已刪物品" })).not.toBeInTheDocument()
    for (const label of ["Pending", "Discarded", "Recognition failed"]) expect(table.getByText(label)).toBeInTheDocument()
    expect(table.getAllByText("Added to inventory")).toHaveLength(2)
    expect(within(screen.getByRole("list")).getByRole("link", { name: "紙本名稱" })).toHaveAttribute("href", "/items/item-1")
    expect(screen.getByText("2 page(s); only the first page is retained")).toBeInTheDocument()
    expect(screen.getByText("Receipt image is unavailable")).toBeInTheDocument()
    const arithmetic = within(screen.getByRole("region", { name: "Arithmetic breakdown" }))
    expect(arithmetic.getByText("Discount")).toBeInTheDocument()
    expect(arithmetic.getAllByText("—").length).toBeGreaterThan(0)
    expect(arithmetic.queryByText(/NT\$/)).not.toBeInTheDocument()
  })
  it("舊快照只呈現已知算術欄位", () => {
    const data = detail()
    delete data.snapshot!.balance_status
    state.query.data = data
    mount()
    const arithmetic = within(screen.getByRole("region", { name: "Arithmetic breakdown" }))
    expect(arithmetic.getByText("Items total")).toBeInTheDocument()
    expect(arithmetic.queryByText("Discount")).not.toBeInTheDocument()
  })
  it("缺快照與空行提供說明及返回入口", () => {
    state.query.data = { receipt_id: "r1", lines: [] }
    mount()
    expect(screen.getByText("No snapshot is available for this receipt")).toBeInTheDocument()
    expect(screen.getByText("No receipt lines. Return to the draft queue.")).toBeInTheDocument()
  })
})
