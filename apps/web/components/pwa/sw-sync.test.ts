// @vitest-environment node
import { readFileSync } from "node:fs"
import { createContext, runInContext } from "node:vm"
import { IDBFactory } from "fake-indexeddb"
import { beforeEach, expect, it, vi } from "vitest"
import type { PendingItem } from "@/lib/offline/storage"

const source = readFileSync(new URL("../../public/sw.js", import.meta.url), "utf8")
const engine = readFileSync(new URL("../../public/offline-engine.js", import.meta.url), "utf8")
const token = `header.${Buffer.from(JSON.stringify({ sub: "owner" })).toString("base64url")}.signature`
let indexedDB: IDBFactory
let db: IDBDatabase
const row: PendingItem = {
  client_id: "one", owner_user_id: "owner", created_at: "2026-01-01", kind: "update", item_id: "item", base_updated_at: "original",
  api_base: "https://ims.test/api", status: "pending", attempts: 0, error_code: null,
  values: { name: "mine", quantity: 1, category_id: null, location_id: null, tag_names: [], custom_values: {} }, customFields: [], trackBatches: false,
  steps: [{ method: "PATCH", path: "/items/item", headers: { "If-Match": "original" }, body: { name: "mine" } }],
}
async function transaction<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("pending-items", mode)
    const request = action(tx.objectStore("pending-items"))
    tx.oncomplete = () => resolve(request.result)
    tx.onerror = () => reject(tx.error)
  })
}
beforeEach(async () => {
  indexedDB = new IDBFactory()
  db = await new Promise((resolve, reject) => {
    const open = indexedDB.open("ims-offline", 1)
    open.onupgradeneeded = () => open.result.createObjectStore("pending-items", { keyPath: "client_id" })
    open.onsuccess = () => resolve(open.result)
    open.onerror = () => reject(open.error)
  })
})
function worker(fetch: ReturnType<typeof vi.fn>, lock?: boolean) {
  const handlers: Record<string, (event: { tag: string; waitUntil(p: Promise<void>): void }) => void> = {}
  const postMessage = vi.fn()
  const locks = lock === undefined ? undefined : { request: vi.fn(async (_name, _options, callback) => callback(lock ? {} : null)) }
  const self = {
    addEventListener: (name: string, callback: typeof handlers[string]) => { handlers[name] = callback },
    clients: { matchAll: vi.fn(async () => [{ postMessage }]) }, navigator: { locks },
  }
  const context = createContext({ self, indexedDB, fetch, atob, URL, console, importScripts: (path: string) => {
    expect(path).toBe("/offline-engine.js")
    runInContext(engine, context)
  } })
  runInContext(source, context)
  return { postMessage, locks, async sync(tag = "ims-offline-sync") {
    let completion: Promise<void> | undefined
    handlers.sync!({ tag, waitUntil: (promise) => { completion = promise } })
    await completion
  } }
}
function refresh() { return new Response(JSON.stringify({ access_token: token }), { status: 200 }) }
it("refreshes with cookies, replays with bearer token and If-Match, persists completion and notifies windows", async () => {
  await transaction("readwrite", (s) => s.put(row))
  const fetch = vi.fn().mockResolvedValueOnce(refresh()).mockResolvedValueOnce(new Response("{}", { status: 200 }))
  const sw = worker(fetch, true)
  await sw.sync()
  expect(sw.locks!.request).toHaveBeenCalledWith("ims-offline-sync", { ifAvailable: true }, expect.any(Function))
  expect(fetch.mock.calls[0]).toEqual(["https://ims.test/api/auth/refresh", { method: "POST", credentials: "include" }])
  expect(fetch.mock.calls[1]).toEqual(["https://ims.test/api/items/item", expect.objectContaining({ method: "PATCH", credentials: "include", headers: expect.objectContaining({ Authorization: `Bearer ${token}`, "If-Match": "original" }), body: JSON.stringify({ name: "mine" }) })])
  expect(await transaction("readonly", (s) => s.getAll())).toEqual([])
  expect(sw.postMessage).toHaveBeenCalledWith({ type: "ims-offline-synced" })
})
it("only handles matching sub, stored steps and pending/syncing records, in creation order", async () => {
  for (const value of [row, { ...row, client_id: "other", owner_user_id: "someone-else" }, { ...row, client_id: "legacy", steps: undefined },
    { ...row, client_id: "conflict", status: "conflict" }, { ...row, client_id: "failed", status: "failed" },
    { ...row, client_id: "earlier", status: "syncing", created_at: "2025-01-01", steps: [{ method: "DELETE", path: "/items/earlier" }] }]) {
    await transaction("readwrite", (s) => s.put(value))
  }
  const fetch = vi.fn().mockResolvedValueOnce(refresh()).mockImplementation(async () => new Response("{}", { status: 200 }))
  await worker(fetch).sync()
  expect(fetch.mock.calls.map(([url]) => url)).toEqual(["https://ims.test/api/auth/refresh", "https://ims.test/api/items/earlier", "https://ims.test/api/items/item"])
  expect((await transaction("readonly", (s) => s.getAll())).map((r: PendingItem) => r.client_id)).toEqual(["conflict", "failed", "legacy", "other"])
})
it("401 refresh leaves items untouched without replay", async () => {
  await transaction("readwrite", (s) => s.put(row))
  const fetch = vi.fn().mockResolvedValue(new Response("{}", { status: 401 }))
  await worker(fetch).sync()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(await transaction("readonly", (s) => s.get("one"))).toEqual(row)
})
it.each(["refresh", "replay"])("%s network failure rejects waitUntil and preserves pending data", async (at) => {
  await transaction("readwrite", (s) => s.put(row))
  const fetch = vi.fn()
  if (at === "replay") fetch.mockResolvedValueOnce(refresh())
  fetch.mockRejectedValue(Error("offline"))
  const sw = worker(fetch)
  await expect(sw.sync()).rejects.toThrow()
  expect(await transaction("readonly", (s) => s.get("one"))).toMatchObject({ status: "pending", attempts: 0 })
  expect(sw.postMessage).toHaveBeenCalledWith({ type: "ims-offline-synced" })
})
it("conflicts are persisted with the current item for review, not system notifications", async () => {
  await transaction("readwrite", (s) => s.put(row))
  const server = { id: "item", updated_at: "new", name: "theirs" }
  const fetch = vi.fn().mockResolvedValueOnce(refresh()).mockResolvedValueOnce(new Response(JSON.stringify({ detail: { current: server } }), { status: 412 }))
  await worker(fetch).sync()
  expect(await transaction("readonly", (s) => s.get("one"))).toMatchObject({ status: "conflict", server, error_code: "item_modified" })
})
it("skips unavailable locks, unrelated tags, and queues with no eligible steps before refreshing", async () => {
  await transaction("readwrite", (s) => s.put(row))
  const fetch = vi.fn()
  const sw = worker(fetch, false)
  await sw.sync()
  await sw.sync("other-tag")
  expect(fetch).not.toHaveBeenCalled()
  expect(await transaction("readonly", (s) => s.get("one"))).toEqual(row)
  await transaction("readwrite", (s) => s.put({ ...row, steps: undefined }))
  await worker(fetch).sync()
  expect(fetch).not.toHaveBeenCalled()
})
it("supplemental network failure removes the completed main operation but rejects the event for remaining work", async () => {
  await transaction("readwrite", (s) => s.put({ ...row, steps: [...row.steps!, { method: "POST", path: "/items/item/custom-values", body: { custom_field_id: 1, value: "mine" } }] }))
  await transaction("readwrite", (s) => s.put({ ...row, client_id: "later", created_at: "2027-01-01" }))
  const fetch = vi.fn().mockResolvedValueOnce(refresh()).mockResolvedValueOnce(new Response("{}", { status: 200 })).mockRejectedValue(Error("offline"))
  const sw = worker(fetch)
  await expect(sw.sync()).rejects.toThrow("offline network failure")
  expect(await transaction("readonly", (s) => s.get("one"))).toBeUndefined()
  expect(await transaction("readonly", (s) => s.get("later"))).toMatchObject({ status: "pending" })
  expect(fetch).toHaveBeenCalledTimes(3)
  expect(sw.postMessage).toHaveBeenCalledWith({ type: "ims-offline-synced" })
})
it("maintains global creation order even when queued API roots differ", async () => {
  for (const [client_id, created_at, api_base] of [
    ["a", "2025-01-01", "https://a.test/api"], ["b", "2025-01-02", "https://b.test/api"], ["c", "2025-01-03", "https://a.test/api"],
  ]) await transaction("readwrite", (s) => s.put({ ...row, client_id, created_at, api_base, steps: [{ method: "DELETE", path: `/items/${client_id}` }] }))
  const fetch = vi.fn(async (url: string) => url.endsWith("/auth/refresh") ? refresh() : new Response(null, { status: 204 }))
  await worker(fetch).sync()
  expect(fetch.mock.calls.map(([url]) => url)).toEqual([
    "https://a.test/api/auth/refresh", "https://a.test/api/items/a", "https://b.test/api/auth/refresh", "https://b.test/api/items/b", "https://a.test/api/items/c",
  ])
})
