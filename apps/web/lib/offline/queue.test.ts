import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiError, NetworkError } from "@/lib/api/client"
import { OfflineQueue, shouldQueue } from "./queue"
import type { OfflineStorage, PendingItem } from "./storage"
import { submitItem } from "./submission"

class MemoryStorage implements OfflineStorage {
  rows = new Map<string, PendingItem>()
  async list(owner: string) {
    return [...this.rows.values()].filter((row) => row.owner_user_id === owner)
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
  }
  async put(item: PendingItem) { this.rows.set(item.client_id, structuredClone(item)) }
  async remove(id: string) { this.rows.delete(id) }
}

function item(id = "one", owner = "owner"): PendingItem {
  return {
    client_id: id, owner_user_id: owner, created_at: `2026-11-14T00:00:0${id === "one" ? 1 : 2}Z`,
    status: "pending", error_code: null, attempts: 0, trackBatches: false, customFields: [],
    values: { name: id, quantity: 2, category_id: null, location_id: null, image_id: "uploaded-image", tag_names: [], custom_values: {} },
  }
}
const auth = () => ({ owner: "owner", token: "token" })
const outcome = { item: { id: "created" }, partial: null } as Awaited<ReturnType<typeof submitItem>>

beforeEach(() => { vi.spyOn(navigator, "onLine", "get").mockReturnValue(true) })

describe("D5、D6、D9 佇列", () => {
  it("新增、讀取、移除與依建立順序同步，隔離其他使用者", async () => {
    const storage = new MemoryStorage()
    const changed = vi.fn(async () => {})
    const send = vi.fn<typeof submitItem>().mockResolvedValue(outcome)
    const queue = new OfflineQueue(storage, changed, send)
    await queue.save(item("two"))
    await queue.save(item())
    await queue.save(item("private", "other"))
    expect((await storage.list("owner")).map((row) => row.client_id)).toEqual(["one", "two"])
    const report = vi.fn()
    await queue.sync(auth, report)
    expect(send.mock.calls.map((call) => call[1])).toEqual(["one", "two"])
    expect(await storage.list("owner")).toEqual([])
    expect(await storage.list("other")).toHaveLength(1)
    expect(changed).toHaveBeenCalled()
    expect(report).toHaveBeenCalledWith({ synced: 2, failed: 0, partial: [] })
  })

  it("同步中狀態可觀察，single-flight 不重送", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    let complete!: (value: typeof outcome) => void
    const send = vi.fn<typeof submitItem>(() => new Promise((resolve) => { complete = resolve }))
    const queue = new OfflineQueue(storage, async () => {}, send)
    const first = queue.sync(auth, vi.fn())
    const second = queue.sync(auth, vi.fn())
    expect(first).toBe(second)
    await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(1))
    expect((await storage.list("owner"))[0]!.status).toBe("syncing")
    complete(outcome)
    await first
    expect(await storage.list("owner")).toEqual([])
  })

  it("App 重開可恢復 syncing，以同一個 key 重放", async () => {
    const storage = new MemoryStorage()
    await storage.put({ ...item(), status: "syncing" })
    const send = vi.fn<typeof submitItem>().mockResolvedValue(outcome)
    await new OfflineQueue(storage, undefined, send).sync(auth, vi.fn())
    expect(send).toHaveBeenCalledWith(expect.objectContaining({ client_id: "one" }), "one", "token")
  })

  it("未登入或仍離線不送出", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    const send = vi.fn<typeof submitItem>()
    const queue = new OfflineQueue(storage, undefined, send)
    await queue.sync(() => null, vi.fn())
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false)
    await queue.sync(auth, vi.fn())
    expect(send).not.toHaveBeenCalled()
  })

  it("同步途中換帳號，不送出下一筆也不向新使用者播報", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    await storage.put(item("two"))
    let owner = "owner"
    const send = vi.fn<typeof submitItem>().mockImplementation(async () => { owner = "other"; return outcome })
    const report = vi.fn()
    await new OfflineQueue(storage, undefined, send).sync(() => ({ owner, token: "token" }), report)
    expect(send).toHaveBeenCalledTimes(1)
    expect((await storage.list("owner"))[0]!.client_id).toBe("two")
    expect(report).not.toHaveBeenCalled()
  })
})

describe("D7 入列判定", () => {
  it("離線與 fetch 傳輸例外入列，一般程式例外不入列", () => {
    expect(shouldQueue(undefined, false)).toBe(true)
    expect(shouldQueue(new NetworkError(new Error("fetch failed")), true)).toBe(true)
    expect(shouldQueue(new TypeError("程式型別錯誤"), true)).toBe(false)
    expect(shouldQueue(new Error("程式錯誤"), true)).toBe(false)
    expect(shouldQueue(new SyntaxError("無效 JSON"), true)).toBe(false)
  })
  it.each([401, 403, 404, 409, 410, 422, 500, 503])("HTTP %i 不入列（含剛斷線）", (status) => {
    expect(shouldQueue(new ApiError(status, null), true)).toBe(false)
    expect(shouldQueue(new ApiError(status, null), false)).toBe(false)
  })
})

describe("D11 失敗分類", () => {
  it("網路失敗維持 pending，不計 attempts，停止本輪", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    await storage.put(item("two"))
    const send = vi.fn<typeof submitItem>().mockRejectedValue(new NetworkError(new Error("斷線")))
    const report = vi.fn()
    await new OfflineQueue(storage, undefined, send).sync(auth, report)
    expect((await storage.list("owner"))[0]).toMatchObject({ status: "pending", attempts: 0, error_code: null })
    expect(send).toHaveBeenCalledTimes(1)
    expect(report).toHaveBeenCalledWith({ synced: 0, failed: 0, partial: [] })
  })

  it("401 暫停整輪，重新登入後可重試", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    await storage.put(item("two"))
    const send = vi.fn<typeof submitItem>().mockRejectedValueOnce(new ApiError(401, null)).mockResolvedValue(outcome)
    const queue = new OfflineQueue(storage, undefined, send)
    await queue.sync(auth, vi.fn())
    expect(send).toHaveBeenCalledTimes(1)
    expect((await storage.list("owner"))[0]).toMatchObject({ status: "pending", attempts: 0 })
    await queue.sync(auth, vi.fn())
    expect(await storage.list("owner")).toEqual([])
  })

  it.each([403, 404, 409, 410, 422])("確定性 HTTP %i 標記 failed，不自動重試並繼續下一筆", async (status) => {
    const storage = new MemoryStorage()
    await storage.put(item())
    await storage.put(item("two"))
    const send = vi.fn<typeof submitItem>().mockRejectedValueOnce(new ApiError(status, null)).mockResolvedValue(outcome)
    const queue = new OfflineQueue(storage, undefined, send)
    const report = vi.fn()
    await queue.sync(auth, report)
    expect((await storage.list("owner"))[0]).toMatchObject({ status: "failed", error_code: String(status) })
    expect(report).toHaveBeenCalledWith({ synced: 1, failed: 1, partial: [] })
    await queue.sync(auth, report)
    expect(send).toHaveBeenCalledTimes(2)
  })

  it.each(["location_id", "category_id"])("%s 不存在保留可讀原因", async (field) => {
    const storage = new MemoryStorage()
    await storage.put(item())
    const send = vi.fn<typeof submitItem>().mockRejectedValue(new ApiError(422, { detail: `${field} not found` }))
    await new OfflineQueue(storage, undefined, send).sync(auth, vi.fn())
    expect((await storage.list("owner"))[0]!.error_code).toBe(field.split("_")[0])
  })

  it("5xx 累計五次才 failed，後續不再自動重試", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    const send = vi.fn<typeof submitItem>().mockRejectedValue(new ApiError(503, null))
    const queue = new OfflineQueue(storage, undefined, send)
    for (let attempts = 1; attempts <= 5; attempts++) {
      await queue.sync(auth, vi.fn())
      expect((await storage.list("owner"))[0]).toMatchObject({ attempts, status: attempts === 5 ? "failed" : "pending" })
    }
    await queue.sync(auth, vi.fn())
    expect(send).toHaveBeenCalledTimes(5)
  })

  it("後續批次／自訂欄位失敗仍移除，回報物品頁供補齊", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    const send = vi.fn<typeof submitItem>().mockResolvedValue({ ...outcome, partial: "batch" })
    const report = vi.fn()
    await new OfflineQueue(storage, undefined, send).sync(auth, report)
    expect(await storage.list("owner")).toEqual([])
    expect(report).toHaveBeenCalledWith({ synced: 1, failed: 0, partial: ["created"] })
  })
})

it("正在編輯的待同步項目不自動送出舊值", async () => {
  const storage = new MemoryStorage()
  await storage.put(item())
  const send = vi.fn<typeof submitItem>().mockResolvedValue(outcome)
  let editing = true
  const queue = new OfflineQueue(storage, undefined, send, () => !editing)
  await queue.sync(auth, vi.fn())
  expect(send).not.toHaveBeenCalled()
  editing = false
  await queue.sync(auth, vi.fn())
  expect(send).toHaveBeenCalledTimes(1)
})

it("新帳號在舊輪次尚未結束時登入，會接續自己的輪次", async () => {
  const storage = new MemoryStorage()
  await storage.put(item())
  await storage.put(item("two", "other"))
  let owner = "owner"
  let complete!: (value: typeof outcome) => void
  const send = vi.fn<typeof submitItem>().mockImplementationOnce(() => new Promise((resolve) => { complete = resolve })).mockResolvedValue(outcome)
  const queue = new OfflineQueue(storage, undefined, send)
  const session = () => ({ owner, token: "token" })
  const first = queue.sync(session, vi.fn())
  await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  owner = "other"
  const second = queue.sync(session, vi.fn())
  complete(outcome)
  await Promise.all([first, second])
  expect(send).toHaveBeenCalledTimes(2)
  expect(send.mock.calls[1]?.[0]).toMatchObject({ owner_user_id: "other" })
  expect(await storage.list("other")).toEqual([])
})


it("同步上一筆時捨棄下一筆，不會從舊快照建立已捨棄物品", async () => {
  const storage = new MemoryStorage()
  await storage.put(item())
  await storage.put(item("two"))
  let complete!: (value: typeof outcome) => void
  const send = vi.fn<typeof submitItem>(() => new Promise((resolve) => { complete = resolve }))
  const queue = new OfflineQueue(storage, undefined, send)
  const flight = queue.sync(auth, vi.fn())
  await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  await queue.remove("two")
  complete(outcome)
  await flight
  expect(send).toHaveBeenCalledTimes(1)
  expect(await storage.list("owner")).toEqual([])
})
