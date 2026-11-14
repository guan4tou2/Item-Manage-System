import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NextIntlClientProvider } from "next-intl"
import { beforeEach, expect, it, vi } from "vitest"
import { toast } from "sonner"

import * as api from "@/lib/api/ai-receipts"
import en from "@/messages/en.json"
import { ReceiptReviewActions } from "./receipt-review-actions"
const flags = vi.hoisted(() => ({ readOnly: false }))
vi.mock("@/lib/auth/use-auth", () => ({ useAccessToken: () => "jwt" }))
vi.mock("@/lib/auth/use-readonly", () => ({ useReadOnly: () => flags.readOnly }))
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }))
vi.mock("@/lib/api/ai-receipts", () => ({ putReceiptReview: vi.fn(), deleteReceiptReview: vi.fn() }))
function mount(verified = false) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(<QueryClientProvider client={qc}><NextIntlClientProvider locale="en" messages={en}>
    <ReceiptReviewActions receiptId="r1" review={verified ? { verified_at: "2026-11-14T00:00:00Z", note: null } : null} />
  </NextIntlClientProvider></QueryClientProvider>)
}
beforeEach(() => { flags.readOnly = false; vi.clearAllMocks() })
it("對話框限制備註長度，顯示字數，失敗會 toast", async () => {
  const user = userEvent.setup()
  vi.mocked(api.putReceiptReview).mockRejectedValue(new Error("離線"))
  mount()
  await user.click(screen.getByRole("button", { name: "Mark as verified" }))
  const input = screen.getByLabelText("Note (optional)")
  expect(input).toHaveAttribute("maxlength", "200")
  await user.type(input, "紙本確認")
  expect(screen.getByText("4/200 characters")).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: "Confirm verification" }))
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith(en.ai.receipts.review.failed))
  expect(api.putReceiptReview).toHaveBeenCalledWith("r1", "紙本確認", "jwt")
})
it("取消核對直接送出，失敗也會 toast", async () => {
  const user = userEvent.setup()
  vi.mocked(api.deleteReceiptReview).mockRejectedValue(new Error("離線"))
  mount(true)
  await user.click(screen.getByRole("button", { name: "Cancel verification" }))
  await waitFor(() => expect(api.deleteReceiptReview).toHaveBeenCalledWith("r1", "jwt"))
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  await waitFor(() => expect(toast.error).toHaveBeenCalled())
})
it("viewer 不渲染動作", () => {
  flags.readOnly = true
  mount()
  expect(screen.queryByRole("button")).not.toBeInTheDocument()
})
