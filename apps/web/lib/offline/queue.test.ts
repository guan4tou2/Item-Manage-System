import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiError, NetworkError } from "@/lib/api/client"
import { OfflineQueue, shouldQueue, requestStep } from "./queue"
import type { OfflineStorage, PendingItem } from "./storage"

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
const outcome = { status: 201, body: { id: "created" } }

beforeEach(() => { vi.spyOn(navigator, "onLine", "get").mockReturnValue(true) })

describe("D5、D6、D9 佇列", () => {
  it("新增、讀取、移除與依建立順序同步，隔離其他使用者", async () => {
    const storage = new MemoryStorage()
    const changed = vi.fn(async () => {})
    const send = vi.fn<typeof requestStep>().mockResolvedValue(outcome)
    const queue = new OfflineQueue(storage, changed, send)
    await queue.save(item("two"))
    await queue.save(item())
    await queue.save(item("private", "other"))
    expect((await storage.list("owner")).map((row) => row.client_id)).toEqual(["one", "two"])
    const report = vi.fn()
    await queue.sync(auth, report)
    expect(send.mock.calls.map((call) => call[0].headers?.["Idempotency-Key"])).toEqual(["one", "two"])
    expect(await storage.list("owner")).toEqual([])
    expect(await storage.list("other")).toHaveLength(1)
    expect(changed).toHaveBeenCalled()
    expect(report).toHaveBeenCalledWith({ synced: 2, failed: 0, partial: [] })
  })

  it("同步中狀態可觀察，single-flight 不重送", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    let complete!: (value: typeof outcome) => void
    const send = vi.fn<typeof requestStep>(() => new Promise((resolve) => { complete = resolve }))
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
    const send = vi.fn<typeof requestStep>().mockResolvedValue(outcome)
    await new OfflineQueue(storage, undefined, send).sync(auth, vi.fn())
    expect(send).toHaveBeenCalledWith(expect.objectContaining({ headers: { "Idempotency-Key": "one" } }), "token")
  })

  it("未登入或仍離線不送出", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    const send = vi.fn<typeof requestStep>()
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
    const send = vi.fn<typeof requestStep>().mockImplementation(async () => { owner = "other"; return outcome })
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
    const send = vi.fn<typeof requestStep>().mockRejectedValue(new NetworkError(new Error("斷線")))
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
    const send = vi.fn<typeof requestStep>().mockResolvedValueOnce({ status: 401, body: null }).mockResolvedValue(outcome)
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
    const send = vi.fn<typeof requestStep>().mockResolvedValueOnce({ status, body: null }).mockResolvedValue(outcome)
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
    const send = vi.fn<typeof requestStep>().mockResolvedValue({ status: 422, body: { detail: `${field} not found` } })
    await new OfflineQueue(storage, undefined, send).sync(auth, vi.fn())
    expect((await storage.list("owner"))[0]!.error_code).toBe(field.split("_")[0])
  })

  it("5xx 累計五次才 failed，後續不再自動重試", async () => {
    const storage = new MemoryStorage()
    await storage.put(item())
    const send = vi.fn<typeof requestStep>().mockResolvedValue({ status: 503, body: null })
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
    await storage.put({ ...item(), trackBatches: true })
    const send = vi.fn<typeof requestStep>().mockResolvedValueOnce(outcome).mockResolvedValueOnce({ status: 503, body: null })
    const report = vi.fn()
    await new OfflineQueue(storage, undefined, send).sync(auth, report)
    expect(await storage.list("owner")).toEqual([])
    expect(report).toHaveBeenCalledWith({ synced: 1, failed: 0, partial: ["created"] })
  })
})

it("正在編輯的待同步項目不自動送出舊值", async () => {
  const storage = new MemoryStorage()
  await storage.put(item())
  const send = vi.fn<typeof requestStep>().mockResolvedValue(outcome)
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
  const send = vi.fn<typeof requestStep>().mockImplementationOnce(() => new Promise((resolve) => { complete = resolve })).mockResolvedValue(outcome)
  const queue = new OfflineQueue(storage, undefined, send)
  const session = () => ({ owner, token: "token" })
  const first = queue.sync(session, vi.fn())
  await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  owner = "other"
  const second = queue.sync(session, vi.fn())
  complete(outcome)
  await Promise.all([first, second])
  expect(send).toHaveBeenCalledTimes(2)
  expect(send.mock.calls[1]?.[0]).toMatchObject({ headers: { "Idempotency-Key": "two" }, body: { name: "two" } })
  expect(await storage.list("other")).toEqual([])
})


it("同步上一筆時捨棄下一筆，不會從舊快照建立已捨棄物品", async () => {
  const storage = new MemoryStorage()
  await storage.put(item())
  await storage.put(item("two"))
  let complete!: (value: typeof outcome) => void
  const send = vi.fn<typeof requestStep>(() => new Promise((resolve) => { complete = resolve }))
  const queue = new OfflineQueue(storage, undefined, send)
  const flight = queue.sync(auth, vi.fn())
  await vi.waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  await queue.remove("two")
  complete(outcome)
  await flight
  expect(send).toHaveBeenCalledTimes(1)
  expect(await storage.list("owner")).toEqual([])
})

it("入列合併同物品並重算 If-Match、步驟與絕對 API root，其他使用者不合併", async () => {
  const storage = new MemoryStorage()
  const queue = new OfflineQueue(storage)
  const original = { ...item(), kind: "update" as const, item_id: "item", base_updated_at: "earliest" }
  await queue.save(original)
  await queue.save({ ...original, owner_user_id: "other", client_id: "other" })
  await queue.save({ ...original, client_id: "new", base_updated_at: "later", values: { ...original.values, name: "latest" } })
  const rows = await storage.list("owner")
  expect(rows).toHaveLength(1)
  expect(rows[0]).toMatchObject({ client_id: "one", base_updated_at: "earliest", values: { name: "latest" }, steps: [{ method: "PATCH", headers: { "If-Match": "earliest" } }] })
  expect(new URL(rows[0]!.api_base!).origin).toBe(location.origin)
  await queue.save({ ...original, kind: "delete", client_id: "delete", base_updated_at: "later" })
  expect((await storage.list("owner"))[0]).toMatchObject({ client_id: "one", kind: "delete", steps: [{ method: "DELETE", headers: { "If-Match": "earliest" } }] })
  await queue.save({ ...original, values: { ...original.values, name: "resurrect" } })
  expect((await storage.list("owner"))[0]!.kind).toBe("delete")
  expect(await storage.list("other")).toHaveLength(1)
})
it("舊資料同步前補算並持久保存步驟，網路失敗仍保留", async () => {
  const storage = new MemoryStorage()
  await storage.put(item())
  const request = vi.fn<typeof requestStep>().mockRejectedValue(new NetworkError("offline"))
  await new OfflineQueue(storage, undefined, request).sync(auth, vi.fn())
  expect((await storage.list("owner"))[0]!.steps).toEqual([expect.objectContaining({ method: "POST", path: "/items", headers: { "Idempotency-Key": "one" } })])
})
it("Web Lock 不可用時跳過整輪，可用時只在鎖內同步", async () => {
  const storage = new MemoryStorage()
  await storage.put(item())
  const request = vi.fn<typeof requestStep>().mockResolvedValue(outcome)
  const locks = { request: vi.fn(async (_name, _options, callback) => callback(null)) }
  Object.defineProperty(navigator, "locks", { configurable: true, value: locks })
  try {
    const queue = new OfflineQueue(storage, undefined, request)
    await queue.sync(auth, vi.fn())
    expect(locks.request).toHaveBeenCalledWith("ims-offline-sync", { ifAvailable: true }, expect.any(Function))
    expect(request).not.toHaveBeenCalled()
    locks.request.mockImplementation(async (_name, _options, callback) => callback({ name: "ims-offline-sync" }))
    await queue.sync(auth, vi.fn())
    expect(request).toHaveBeenCalledTimes(1)
  } finally { Object.defineProperty(navigator, "locks", { configurable: true, value: undefined }) }
})
it("conflict stays queued until explicitly resolved with the server version", async () => {
  const storage = new MemoryStorage()
  const row = { ...item(), kind: "update" as const, item_id: "item", base_updated_at: "old" }
  await storage.put(row)
  const request = vi.fn<typeof requestStep>().mockResolvedValueOnce({ status: 412, body: { detail: { current: { updated_at: "server" } } } }).mockResolvedValue(outcome)
  const queue = new OfflineQueue(storage, undefined, request)
  await queue.sync(auth, vi.fn())
  const conflict = (await storage.list("owner"))[0]!
  expect(conflict.status).toBe("conflict")
  await queue.sync(auth, vi.fn())
  expect(request).toHaveBeenCalledTimes(1)
  await queue.resolveConflict(conflict)
  await queue.sync(auth, vi.fn())
  expect(request.mock.calls[1]![0].headers).toEqual({ "If-Match": "server" })
  expect(await storage.list("owner")).toEqual([])
})
