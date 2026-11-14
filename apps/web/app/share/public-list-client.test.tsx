import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, describe, expect, it, vi } from "vitest"

import * as api from "@/lib/api/public-list"
import en from "@/messages/en.json"
import { PublicListClient } from "./public-list-client"

vi.mock("@/lib/api/public-list", async importOriginal => ({
  ...await importOriginal<typeof api>(), getPublicList: vi.fn(),
}))
const data: api.PublicList = {
  kind: "shopping", title: "Camping", description: "For tomorrow",
  start_date: "2026-11-15", end_date: "2026-11-16",
  entries: [{ name: "Tent", quantity: 2, note: "Large", link: "javascript:alert(1)", is_done: true }],
}
function show() {
  return render(<NextIntlClientProvider locale="en" messages={en}><PublicListClient /></NextIntlClientProvider>)
}
beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState({}, "", "/share#secret")
  vi.mocked(api.getPublicList).mockResolvedValue(data)
})

describe("公開分享頁", () => {
  it("沒有 fragment 時引導索取連結，且不發請求", async () => {
    window.history.replaceState({}, "", "/share")
    show()
    expect(await screen.findByText(en.publicList.missing)).toBeVisible()
    expect(api.getPublicList).not.toHaveBeenCalled()
    expect(screen.getByText(en.publicList.invalidHelp)).toBeVisible()
  })
  it("載入中顯示狀態", () => {
    vi.mocked(api.getPublicList).mockReturnValue(new Promise(() => {}))
    show()
    expect(screen.getByRole("status", { name: en.publicList.loading })).toBeVisible()
  })
  it("無效與過期使用相同訊息", async () => {
    vi.mocked(api.getPublicList).mockRejectedValue(new api.PublicListError(404))
    show()
    expect(await screen.findByText(en.publicList.invalid)).toBeVisible()
    expect(screen.queryByRole("button", { name: en.publicList.retry })).not.toBeInTheDocument()
  })
  it("網路失敗可重試", async () => {
    vi.mocked(api.getPublicList).mockRejectedValueOnce(new TypeError("offline"))
    show()
    fireEvent.click(await screen.findByRole("button", { name: en.publicList.retry }))
    expect(await screen.findByText("Camping")).toBeVisible()
    expect(api.getPublicList).toHaveBeenCalledTimes(2)
  })
  it("唯讀、文字標示完成、危險連結不成為超連結、預設不顯示金額", async () => {
    show()
    expect(await screen.findByText("Tent")).toHaveClass("line-through")
    expect(screen.getByText(en.publicList.done)).toBeVisible()
    expect(screen.getByText("javascript:alert(1)")).toBeVisible()
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument()
    expect(screen.queryByText(/Budget|Price/)).not.toBeInTheDocument()
    expect(screen.getByText(en.publicList.readonly)).toBeVisible()
    expect(api.getPublicList).toHaveBeenCalledWith("secret", expect.any(AbortSignal))
  })
  it("允許 http(s) 連結並使用安全屬性，依帳號幣別呈現金額", async () => {
    vi.mocked(api.getPublicList).mockResolvedValue({ ...data, budget: "5000", currency: "TWD",
      entries: [{ ...data.entries[0]!, link: "https://example.com", price: "1200" }],
    })
    show()
    const link = await screen.findByRole("link")
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer nofollow")
    expect(screen.getByText("Budget: NT$5,000")).toBeVisible()
    expect(screen.getByText("Price: NT$1,200")).toBeVisible()
  })
  it("空清單給出下一步", async () => {
    vi.mocked(api.getPublicList).mockResolvedValue({ ...data, entries: [] })
    show()
    expect(await screen.findByText(en.publicList.empty)).toBeVisible()
  })
  it("fragment 改變後重新讀取，不保留先前清單", async () => {
    show()
    await screen.findByText("Camping")
    window.history.replaceState({}, "", "/share#other")
    act(() => window.dispatchEvent(new Event("hashchange")))
    await waitFor(() => expect(api.getPublicList).toHaveBeenLastCalledWith("other", expect.any(AbortSignal)))
  })
})
