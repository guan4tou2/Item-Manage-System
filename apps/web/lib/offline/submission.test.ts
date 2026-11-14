import { beforeEach, expect, it, vi } from "vitest"
import { createBatch } from "@/lib/api/batches"
import { saveItemCustomValues } from "@/lib/api/customization"
import { createItem, type ItemRead } from "@/lib/api/items"
import { submitItem, type ItemSubmission } from "./submission"

vi.mock("@/lib/api/batches", () => ({ createBatch: vi.fn() }))
vi.mock("@/lib/api/customization", () => ({ saveItemCustomValues: vi.fn() }))
vi.mock("@/lib/api/items", () => ({ createItem: vi.fn() }))
const draft: ItemSubmission = {
  values: { name: "電池", quantity: 4, cost: "15.50", category_id: null, location_id: 2, image_id: "image", tag_names: ["備品"], custom_values: { "1": "值" } },
  trackBatches: true, customFields: [{ id: 1 } as never],
}
beforeEach(() => { vi.resetAllMocks(); vi.mocked(createItem).mockResolvedValue({ id: "item" } as ItemRead) })

it("線上與重放共用相同 payload、key 與依序後續步驟", async () => {
  const order: string[] = []
  vi.mocked(createItem).mockImplementation(async () => { order.push("item"); return { id: "item" } as ItemRead })
  vi.mocked(createBatch).mockImplementation(async () => { order.push("batch"); return {} as never })
  vi.mocked(saveItemCustomValues).mockImplementation(async () => { order.push("custom") })
  const result = await submitItem(draft, "key", "token")
  expect(createItem).toHaveBeenCalledWith({ name: "電池", quantity: 4, cost: "15.50", category_id: undefined, location_id: 2, image_id: "image", tag_names: ["備品"], description: undefined, barcode: undefined, notes: undefined }, "token", "key")
  expect(createBatch).toHaveBeenCalledWith("item", {}, "token")
  expect(saveItemCustomValues).toHaveBeenCalledWith("item", draft.customFields, { "1": "值" }, "token")
  expect(order).toEqual(["item", "batch", "custom"])
  expect(result.partial).toBeNull()
})
it("未啟用追蹤時不建批次", async () => {
  await submitItem({ ...draft, trackBatches: false }, "key", "token")
  expect(createBatch).not.toHaveBeenCalled()
  expect(saveItemCustomValues).toHaveBeenCalled()
})
it("批次失敗回報 partial，停止自訂欄位步驟", async () => {
  vi.mocked(createBatch).mockRejectedValue(new TypeError("網路"))
  expect((await submitItem(draft, "key", "token")).partial).toBe("batch")
  expect(saveItemCustomValues).not.toHaveBeenCalled()
})
it("自訂欄位失敗回報 partial，不拋出可再次建立的例外", async () => {
  vi.mocked(saveItemCustomValues).mockRejectedValue(new Error("錯誤"))
  expect((await submitItem(draft, "key", "token")).partial).toBe("custom")
})
