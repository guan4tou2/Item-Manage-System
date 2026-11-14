import { afterEach, expect, it, vi } from "vitest"

import { createShare, listShares, revokeShare } from "./list-shares"
import { apiFetch } from "./client"

vi.mock("./client", () => ({ apiFetch: vi.fn() }))
afterEach(() => vi.clearAllMocks())

it("分享管理請求沿用登入 client，建立選項完整送出", async () => {
  vi.mocked(apiFetch).mockResolvedValue({ json: async () => [] } as unknown as Response)
  await listShares("l1", "jwt")
  expect(apiFetch).toHaveBeenLastCalledWith("/lists/l1/shares", { accessToken: "jwt" })
  for (const days of [1, 7, 30, null] as const) {
    await createShare("l1", { expires_in_days: days, show_prices: true }, "jwt")
    expect(apiFetch).toHaveBeenLastCalledWith("/lists/l1/shares", {
      accessToken: "jwt", method: "POST", body: JSON.stringify({ expires_in_days: days, show_prices: true }),
    })
  }
  await revokeShare("l1", "s1", "jwt")
  expect(apiFetch).toHaveBeenLastCalledWith("/lists/l1/shares/s1", { method: "DELETE", accessToken: "jwt" })
})
