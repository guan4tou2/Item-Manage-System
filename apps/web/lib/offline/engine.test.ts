import { describe, expect, it, vi } from "vitest"
import { executeItem, applyResult, failureCode, type EngineItem } from "./engine"

const row: EngineItem = { kind: "update", item_id: "item", steps: [{ method: "PATCH", path: "/items/item", headers: { "If-Match": "original" } }], status: "syncing", attempts: 0, error_code: null }
describe("shared replay engine", () => {
  it.each([200, 201, 204])("%i removes a completed item", async (status) => {
    const result = await executeItem(row, async () => ({ status, body: null }))
    expect(result).toEqual({ type: "success", item_id: "item" })
    expect(applyResult(row, result)).toBeNull()
  })
  it("network failure and 401 pause with no attempt counted", async () => {
    for (const request of [async () => { throw Error("offline") }, async () => ({ status: 401, body: null })]) {
      const outcome = await executeItem(row, request)
      expect(["network", "unauthorized"]).toContain(outcome.type)
      expect(applyResult(row, outcome)).toMatchObject({ status: "pending", attempts: 0, error_code: null })
    }
  })
  it("412 preserves detail.current without mutating the input", async () => {
    const server = { id: "item", name: "server", updated_at: "new" }
    const outcome = await executeItem(row, async () => ({ status: 412, body: { detail: { code: "item_modified", current: server } } }))
    expect(outcome).toEqual({ type: "conflict", server })
    expect(applyResult(row, outcome)).toMatchObject({ status: "conflict", server, error_code: "item_modified" })
    expect(row.status).toBe("syncing")
  })
  it("delete 404 completes, update 404 reports a missing item", async () => {
    const request = async () => ({ status: 404, body: null })
    expect(applyResult(row, await executeItem({ ...row, kind: "delete" }, request))).toBeNull()
    expect(applyResult(row, await executeItem(row, request))).toMatchObject({ status: "failed", error_code: "item_gone" })
  })
  it.each([403, 409, 410, 422])("%i fails permanently", async (status) => {
    const result = await executeItem(row, async () => ({ status, body: { detail: { code: "specific" } } }))
    expect(applyResult(row, result)).toMatchObject({ status: "failed", error_code: "specific" })
  })
  it("5xx consumes one attempt and fails on the fifth", async () => {
    const result = await executeItem(row, async () => ({ status: 503, body: null }))
    expect(applyResult(row, result)).toMatchObject({ status: "pending", attempts: 1, error_code: "server" })
    expect(applyResult({ ...row, attempts: 4 }, result)).toMatchObject({ status: "failed", attempts: 5 })
  })
  it("substitutes the created ID in every supplemental path, retaining bodies and headers", async () => {
    const request = vi.fn().mockResolvedValueOnce({ status: 201, body: { id: "a/b" } }).mockResolvedValue({ status: 204, body: null })
    const create: EngineItem = { ...row, kind: undefined, item_id: undefined, steps: [
      { method: "POST", path: "/items", headers: { "Idempotency-Key": "key" }, body: { name: "mine" } },
      { method: "POST", path: "/items/{item_id}/batches", body: {} },
      { method: "DELETE", path: "/items/{item_id}/custom-values/1", tolerate404: true },
    ] }
    expect(await executeItem(create, request)).toEqual({ type: "success", item_id: "a/b" })
    expect(request.mock.calls.map(([step]) => step.path)).toEqual(["/items", "/items/a%2Fb/batches", "/items/a%2Fb/custom-values/1"])
    expect(request.mock.calls[0]![0]).toEqual(create.steps![0])
  })
  it.each(["http", "network", "unauthorized"])("supplemental %s failure is partial and stops remaining steps", async (failure) => {
    const request = vi.fn().mockResolvedValueOnce({ status: 201, body: { id: "created" } })
    if (failure === "network") request.mockRejectedValueOnce(Error("offline"))
    else request.mockResolvedValueOnce({ status: failure === "http" ? 500 : 401, body: null })
    const result = await executeItem({ ...row, kind: "create", steps: [{ method: "POST", path: "/items" }, { method: "POST", path: "/items/{item_id}/batches" }, { method: "POST", path: "/never" }] }, request)
    expect(result).toEqual({ type: "partial", item_id: "created", ...(failure === "network" ? { network: true } : {}) })
    expect(applyResult(row, result)).toBeNull()
    expect(request).toHaveBeenCalledTimes(2)
  })
  it("only custom-value delete opts into tolerating 404", async () => {
    const request = vi.fn().mockResolvedValueOnce({ status: 200, body: {} }).mockResolvedValueOnce({ status: 404, body: null })
    expect((await executeItem({ ...row, steps: [...row.steps!, { method: "DELETE", path: "/custom", tolerate404: true }] }, request)).type).toBe("success")
  })
  it("never sends unresolved placeholders or empty step lists", async () => {
    const request = vi.fn().mockResolvedValue({ status: 201, body: {} })
    const result = await executeItem({ ...row, kind: "create", item_id: undefined, steps: [{ method: "POST", path: "/items" }, { method: "POST", path: "/items/{item_id}/batches" }] }, request)
    expect(result.type).toBe("partial")
    expect(request).toHaveBeenCalledTimes(1)
    expect((await executeItem({ ...row, steps: [] }, request)).type).toBe("failed")
  })
  it("preserves Phase 51 failure codes", () => {
    expect(failureCode({ status: 422, body: { detail: "location_id missing" } })).toBe("location")
    expect(failureCode({ status: 422, body: { detail: "category_id missing" } })).toBe("category")
    expect(failureCode({ status: 410, body: { code: "deleted" } })).toBe("deleted")
    expect(failureCode({ status: 403, body: null })).toBe("403")
  })
})
