import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import zhMessages from "@/messages/zh-TW.json"

const toastError = vi.fn()
const toastSuccess = vi.fn()

vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => toastError(...args),
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}))

vi.mock("@/lib/auth/use-auth", () => ({
  useAccessToken: () => "jwt",
}))

vi.mock("@/lib/api/batches", () => ({
  listBatches: vi.fn(),
  createBatch: vi.fn(),
  updateBatch: vi.fn(),
  deleteBatch: vi.fn(),
  consumeBatch: vi.fn(),
  consumeFefo: vi.fn(),
  disableBatches: vi.fn(),
}))

import * as api from "@/lib/api/batches"
import type { BatchRead } from "@/lib/api/batches"
import { taipeiTodayIso } from "./expiry-badge"
import { BatchSection } from "./batch-section"

function iso(offsetDays: number): string {
  const base = Date.parse(`${taipeiTodayIso()}T00:00:00Z`)
  return new Date(base + offsetDays * 86_400_000).toISOString().slice(0, 10)
}

function batch(overrides: Partial<BatchRead> = {}): BatchRead {
  return {
    id: "batch-1",
    quantity: 5,
    expiry_date: null,
    note: null,
    is_depleted: false,
    ...overrides,
  } as BatchRead
}

function renderSection(canEdit = true, defaultCost: string | null = null, currency = "TWD") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale="zh-TW" messages={zhMessages}>
        <BatchSection itemId="item-1" canEdit={canEdit} defaultCost={defaultCost} currency={currency} />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  )
}

describe("BatchSection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("顯示到期 badge：過期紅、7 天內橙、其餘中性", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([
      batch({ id: "b-exp", expiry_date: iso(-3) }),
      batch({ id: "b-soon", expiry_date: iso(2) }),
      batch({ id: "b-ok", expiry_date: iso(30) }),
    ])

    renderSection()

    const expired = await screen.findByText("過期 3 天")
    expect(expired).toHaveAttribute("data-status", "expired")
    expect(expired.className).toContain("text-destructive")

    const soon = screen.getByText("剩 2 天")
    expect(soon).toHaveAttribute("data-status", "expiring")
    expect(soon.className).toContain("text-warning")

    expect(screen.getByText(iso(30))).toHaveAttribute("data-status", "ok")
  })

  it("載入中顯示 skeleton", () => {
    vi.mocked(api.listBatches).mockImplementation(() => new Promise(() => {}))

    const { container } = renderSection()

    expect(container.querySelector(".animate-pulse")).not.toBeNull()
  })

  it("−1 立即樂觀扣減", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([batch({ id: "b1", quantity: 5 })])
    vi.mocked(api.consumeBatch).mockImplementation(() => new Promise(() => {}))

    renderSection()

    fireEvent.click(await screen.findByRole("button", { name: "消耗 1（剩餘 5）" }))

    expect(await screen.findByText("剩 4")).toBeInTheDocument()
  })

  it("鍵盤可達操作鈕且消耗回饋走 aria-live", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([batch({ id: "b1", quantity: 2 })])
    vi.mocked(api.consumeBatch).mockResolvedValue(batch({ id: "b1", quantity: 1 }))

    renderSection()

    const restock = await screen.findByRole("button", { name: "進貨／調整" })
    restock.focus()
    expect(restock).toHaveFocus()

    const consumeButton = screen.getByRole("button", { name: "消耗 1（剩餘 2）" })
    consumeButton.focus()
    expect(consumeButton).toHaveFocus()

    fireEvent.click(consumeButton)

    await waitFor(() =>
      expect(screen.getByText("已消耗 1", { selector: "[aria-live]" })).toBeInTheDocument(),
    )
  })

  it("−1 失敗時回滾並 toast", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([batch({ id: "b1", quantity: 5 })])
    vi.mocked(api.consumeBatch).mockRejectedValue(new Error("boom"))

    renderSection()

    fireEvent.click(await screen.findByRole("button", { name: "消耗 1（剩餘 5）" }))

    await waitFor(() => expect(toastError).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText("剩 5")).toBeInTheDocument())
  })

  it("已耗盡區塊預設收起、點擊後展開", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([
      batch({ id: "b1", quantity: 3 }),
      batch({ id: "b2", quantity: 0, is_depleted: true, note: "舊批次" }),
    ])

    renderSection()

    const toggle = await screen.findByRole("button", { name: /已耗盡（1）/ })
    expect(toggle).toHaveAttribute("aria-expanded", "false")
    expect(screen.queryByText("舊批次")).not.toBeInTheDocument()

    fireEvent.click(toggle)

    expect(screen.getByText("舊批次")).toBeInTheDocument()
    expect(toggle).toHaveAttribute("aria-expanded", "true")
  })

  it("清零後該列移入已耗盡", async () => {
    vi.mocked(api.listBatches)
      .mockResolvedValueOnce([batch({ id: "b1", quantity: 1 })])
      .mockResolvedValue([batch({ id: "b1", quantity: 0, is_depleted: true })])
    vi.mocked(api.consumeBatch).mockResolvedValue(
      batch({ id: "b1", quantity: 0, is_depleted: true }),
    )

    renderSection()

    fireEvent.click(await screen.findByRole("button", { name: "消耗 1（剩餘 1）" }))

    expect(await screen.findByRole("button", { name: /已耗盡（1）/ })).toBeInTheDocument()
    expect(screen.queryByText("剩 1")).not.toBeInTheDocument()
  })

  it("關閉追蹤：對話框文案與呼叫 disable 端點", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([batch()])
    vi.mocked(api.disableBatches).mockResolvedValue({ id: "item-1", track_batches: false } as never)

    renderSection()

    fireEvent.click(await screen.findByRole("button", { name: "關閉追蹤" }))

    const dialog = await screen.findByRole("alertdialog")
    expect(
      within(dialog).getByText("批次將合併為單一數量，所有批次到期日與成本資訊將被刪除。"),
    ).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole("button", { name: "關閉追蹤" }))

    await waitFor(() => expect(api.disableBatches).toHaveBeenCalledWith("item-1", "jwt"))
  })

  it("空狀態顯示建立第一批引導", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([])

    renderSection()

    expect(await screen.findByText("尚未建立任何批次。")).toBeInTheDocument()
    expect(screen.getByText("按「進貨／調整」建立第一批。")).toBeInTheDocument()
  })

  it("進貨表單送出建立批次", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([])
    vi.mocked(api.createBatch).mockResolvedValue(batch())

    renderSection()

    fireEvent.click(await screen.findByRole("button", { name: "進貨／調整" }))
    fireEvent.change(screen.getByLabelText("數量"), { target: { value: "3" } })
    fireEvent.change(screen.getByLabelText("到期日"), { target: { value: "2026-12-01" } })
    fireEvent.click(screen.getByRole("button", { name: "建立" }))

    await waitFor(() =>
      expect(api.createBatch).toHaveBeenCalledWith(
        "item-1",
        { quantity: 3, expiry_date: "2026-12-01", note: null, unit_cost: null },
        "jwt",
      ),
    )
  })

  it("唯讀模式不顯示操作按鈕", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([batch({ id: "b1", quantity: 5 })])

    renderSection(false)

    expect(await screen.findByText("剩 5")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "進貨／調整" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /消耗 1/ })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "關閉追蹤" })).not.toBeInTheDocument()
  })
})


describe("批次成本", () => {
  beforeEach(() => vi.clearAllMocks())

  it.each(["-1", "1.234", "NaN", "10000000000"])("成本 %s 即時提示且阻擋新增", async (cost) => {
    vi.mocked(api.listBatches).mockResolvedValue([])
    renderSection()
    fireEvent.click(await screen.findByRole("button", { name: "進貨／調整" }))
    fireEvent.change(screen.getByLabelText("數量"), { target: { value: "3" } })
    fireEvent.change(screen.getByLabelText("單位成本（NT$）"), { target: { value: cost } })
    expect(screen.getByRole("alert")).toHaveTextContent("成本需為數字")
    expect(screen.getByRole("button", { name: "建立" })).toBeDisabled()
    fireEvent.click(screen.getByRole("button", { name: "建立" }))
    expect(api.createBatch).not.toHaveBeenCalled()
  })

  it("新增可送出有效成本，提示帳號幣別與預設單價", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([])
    vi.mocked(api.createBatch).mockResolvedValue(batch())
    renderSection(true, "10", "USD")
    fireEvent.click(await screen.findByRole("button", { name: "進貨／調整" }))
    expect(screen.getByText(/留白時使用物品的預設單價（US\$10）/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("數量"), { target: { value: "3" } })
    fireEvent.change(screen.getByLabelText("單位成本（US$）"), { target: { value: "12.30" } })
    fireEvent.click(screen.getByRole("button", { name: "建立" }))
    await waitFor(() => expect(api.createBatch).toHaveBeenCalledWith("item-1", {
      quantity: 3, expiry_date: null, note: null, unit_cost: "12.30",
    }, "jwt"))
  })

  it("編輯預填成本，清空送出 null 並保留數量到期與備註", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([batch({ unit_cost: "12.30", expiry_date: "2027-01-01", note: "保留" })])
    vi.mocked(api.updateBatch).mockResolvedValue(batch({ unit_cost: null }))
    renderSection(true, "10")
    fireEvent.click(await screen.findByRole("button", { name: "編輯" }))
    const input = screen.getByLabelText("單位成本（NT$）")
    expect(input).toHaveValue("12.30")
    fireEvent.change(input, { target: { value: "-1" } })
    expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled()
    fireEvent.change(input, { target: { value: "  " } })
    fireEvent.click(screen.getByRole("button", { name: "儲存" }))
    await waitFor(() => expect(api.updateBatch).toHaveBeenCalledWith("item-1", "batch-1", {
      quantity: 5, expiry_date: "2027-01-01", note: "保留", unit_cost: null,
    }, "jwt"))
  })

  it("批次單價含零且不重複預設單價，小計忽略耗盡批次", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([
      batch({ id: "a", quantity: 2, unit_cost: "3" }),
      batch({ id: "b", quantity: 2, unit_cost: null }),
      batch({ id: "c", quantity: 1, unit_cost: "0" }),
      batch({ id: "d", quantity: 0, is_depleted: true, unit_cost: "99" }),
    ])
    renderSection(false, "10")
    expect(await screen.findByText("NT$3")).toHaveClass("tabular-nums")
    expect(screen.getByText("NT$0")).toBeInTheDocument()
    expect(screen.queryByText("NT$10")).not.toBeInTheDocument()
    expect(screen.getByTestId("batch-valuation")).toHaveTextContent("估值 NT$26")
    expect(screen.queryByRole("button", { name: "編輯" })).not.toBeInTheDocument()
  })

  it("沒有批次成本不顯示小計", async () => {
    vi.mocked(api.listBatches).mockResolvedValue([batch({ unit_cost: null })])
    renderSection(true, "10")
    await screen.findByText("剩 5")
    expect(screen.queryByTestId("batch-valuation")).not.toBeInTheDocument()
  })

  it("載入錯誤提供重試而不呈現空狀態", async () => {
    vi.mocked(api.listBatches).mockRejectedValueOnce(new Error("離線")).mockResolvedValue([batch()])
    renderSection()
    expect(await screen.findByRole("alert")).toHaveTextContent("無法載入批次")
    expect(screen.queryByText("尚未建立任何批次。")).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "重試" }))
    expect(await screen.findByText("剩 5")).toBeInTheDocument()
  })
})
