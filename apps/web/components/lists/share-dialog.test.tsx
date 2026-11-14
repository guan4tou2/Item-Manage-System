import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as api from "@/lib/api/list-shares"
import { ApiError } from "@/lib/api/client"
import en from "@/messages/en.json"
import { ShareDialog } from "./share-dialog"

vi.mock("@/lib/auth/use-auth", () => ({ useAccessToken: () => "jwt" }))
vi.mock("@/lib/api/list-shares", () => ({ listShares: vi.fn(), createShare: vi.fn(), revokeShare: vi.fn() }))
const t = en.listShare
const existing = { id: "s1", token_prefix: "abcdef", show_prices: false, expires_at: null,
  created_at: "2026-11-14T00:00:00Z", last_accessed_at: null, access_count: 0 }
function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const result = render(<QueryClientProvider client={client}><NextIntlClientProvider locale="en" messages={en}><ShareDialog listId="l1" /></NextIntlClientProvider></QueryClientProvider>)
  fireEvent.click(screen.getByRole("button", { name: t.title }))
  return { ...result, client }
}
beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listShares).mockResolvedValue([])
  vi.mocked(api.createShare).mockResolvedValue({ ...existing, token: "secret-once" })
  vi.mocked(api.revokeShare).mockResolvedValue(undefined)
})

describe("分享對話框", () => {
  it("空狀態與安全預設：7 天、價格關閉", async () => {
    show()
    expect(await screen.findByText(t.empty)).toBeVisible()
    expect(screen.getByRole("combobox")).toHaveTextContent("7 days")
    expect(screen.getByRole("switch", { name: t.showPrices })).not.toBeChecked()
  })
  it("載入時顯示骨架並阻止建立", () => {
    vi.mocked(api.listShares).mockReturnValue(new Promise(() => {}))
    show()
    expect(screen.getByRole("status", { name: t.loading })).toBeVisible()
    expect(screen.getByRole("button", { name: t.create })).toBeDisabled()
  })
  it("建立中停用按鈕並顯示進度", async () => {
    vi.mocked(api.createShare).mockReturnValue(new Promise(() => {}))
    show()
    await screen.findByText(t.empty)
    fireEvent.click(screen.getByRole("button", { name: t.create }))
    expect(await screen.findByRole("button", { name: t.creating })).toBeDisabled()
    expect(screen.getByRole("switch")).toBeDisabled()
    expect(screen.getByRole("combobox")).toBeDisabled()
  })
  it("載入失敗可重試", async () => {
    vi.mocked(api.listShares).mockRejectedValueOnce(new Error("offline"))
    show()
    fireEvent.click(await screen.findByRole("button", { name: t.retry }))
    expect(await screen.findByText(t.empty)).toBeVisible()
  })
  it("建立後複製 fragment 網址，關閉重開不再顯示，也不保留 mutation token", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } })
    const { client } = show()
    await screen.findByText(t.empty)
    fireEvent.click(screen.getByRole("button", { name: t.create }))
    const input = await screen.findByLabelText(t.url)
    const url = `${window.location.origin}/share#secret-once`
    expect(input).toHaveValue(url)
    expect(screen.getByText(t.once)).toBeVisible()
    expect(api.createShare).toHaveBeenCalledWith("l1", { expires_in_days: 7, show_prices: false }, "jwt")
    fireEvent.click(screen.getByRole("button", { name: t.copy }))
    expect(await screen.findByText(t.copied)).toBeVisible()
    expect(writeText).toHaveBeenCalledWith(url)
    fireEvent.click(screen.getByRole("button", { name: "Close" }))
    fireEvent.click(screen.getByRole("button", { name: t.title }))
    expect(screen.queryByLabelText(t.url)).not.toBeInTheDocument()
    expect(JSON.stringify(client.getMutationCache().getAll().map(m => m.state.data))).not.toContain("secret-once")
  })
  it("複製失敗提供可選取的唯讀網址", async () => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } })
    show()
    await screen.findByText(t.empty)
    fireEvent.click(screen.getByRole("button", { name: t.create }))
    const input = await screen.findByLabelText(t.url) as HTMLInputElement
    fireEvent.click(screen.getByRole("button", { name: t.copy }))
    expect(await screen.findByText(t.copyFallback)).toBeVisible()
    expect(input).toHaveAttribute("readonly")
    fireEvent.focus(input)
    expect(input.selectionStart).toBe(0)
    expect(input.selectionEnd).toBe(input.value.length)
  })
  it("顯示既有連結的所有資訊並確認撤銷", async () => {
    vi.mocked(api.listShares).mockResolvedValue([existing])
    show()
    expect(await screen.findByText("abcdef…")).toBeVisible()
    for (const label of [t.createdAt, t.expiresAt, t.lastAccessed, t.accessCount, t.never]) expect(screen.getByText(label)).toBeVisible()
    fireEvent.click(screen.getByRole("button", { name: t.revoke }))
    const confirm = screen.getByRole("alertdialog")
    expect(api.revokeShare).not.toHaveBeenCalled()
    fireEvent.click(within(confirm).getByRole("button", { name: t.revoke }))
    await waitFor(() => expect(api.revokeShare).toHaveBeenCalledWith("l1", "s1", "jwt"))
  })
  it("達上限時禁止建立", async () => {
    vi.mocked(api.listShares).mockResolvedValue(Array.from({ length: 5 }, (_, i) => ({ ...existing, id: String(i) })))
    show()
    expect(await screen.findByText(t.limit)).toBeVisible()
    expect(screen.getByRole("button", { name: t.create })).toBeDisabled()
  })
  it.each([409, 500])("建立失敗 %s 給明確錯誤", async status => {
    vi.mocked(api.createShare).mockRejectedValue(new ApiError(status, null))
    show()
    await screen.findByText(t.empty)
    fireEvent.click(screen.getByRole("button", { name: t.create }))
    expect(await screen.findByText(status === 409 ? t.limit : t.createError)).toBeVisible()
    expect(screen.queryByLabelText(t.url)).not.toBeInTheDocument()
  })
  it("撤銷失敗保留連結並顯示錯誤", async () => {
    vi.mocked(api.listShares).mockResolvedValue([existing])
    vi.mocked(api.revokeShare).mockRejectedValue(new Error("offline"))
    show()
    fireEvent.click(await screen.findByRole("button", { name: t.revoke }))
    fireEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: t.revoke }))
    expect(await screen.findByText(t.revokeError)).toBeVisible()
    expect(screen.getByText("abcdef…")).toBeVisible()
  })
})
