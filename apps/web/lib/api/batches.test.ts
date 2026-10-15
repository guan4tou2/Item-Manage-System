import { afterEach, describe, expect, it, vi } from "vitest"

import {
  consumeBatch,
  consumeFefo,
  createBatch,
  deleteBatch,
  disableBatches,
  listBatches,
  updateBatch,
} from "./batches"

const originalFetch = global.fetch

function mockJson(body: unknown, status = 200) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  )
}

function lastCall() {
  const call = vi.mocked(global.fetch).mock.calls.at(-1)
  return { url: call?.[0] as string, init: call?.[1] as RequestInit }
}

describe("batches api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("lists batches for an item", async () => {
    mockJson([{ id: "b1", quantity: 2 }])

    const result = await listBatches("item-1", "jwt")

    expect(result).toHaveLength(1)
    const { url, init } = lastCall()
    expect(url).toBe("/api/items/item-1/batches")
    expect(init.method).toBeUndefined()
    expect((init.headers as Headers).get("authorization")).toBe("Bearer jwt")
  })

  it("creates a batch with the serialized payload", async () => {
    mockJson({ id: "b1" }, 201)

    await createBatch("item-1", { quantity: 3, expiry_date: "2026-11-01", note: "costco" }, "jwt")

    const { url, init } = lastCall()
    expect(url).toBe("/api/items/item-1/batches")
    expect(init.method).toBe("POST")
    expect(init.body).toBe(
      JSON.stringify({ quantity: 3, expiry_date: "2026-11-01", note: "costco" }),
    )
  })

  it("updates a batch", async () => {
    mockJson({ id: "b1" })

    await updateBatch("item-1", "b1", { quantity: 5 }, "jwt")

    const { url, init } = lastCall()
    expect(url).toBe("/api/items/item-1/batches/b1")
    expect(init.method).toBe("PATCH")
    expect(init.body).toBe(JSON.stringify({ quantity: 5 }))
  })

  it("deletes a batch without parsing a body", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))

    await expect(deleteBatch("item-1", "b1", "jwt")).resolves.toBeUndefined()

    const { url, init } = lastCall()
    expect(url).toBe("/api/items/item-1/batches/b1")
    expect(init.method).toBe("DELETE")
  })

  it("consumes a single batch", async () => {
    mockJson({ id: "b1", quantity: 1 })

    await consumeBatch("item-1", "b1", { quantity: 1 }, "jwt")

    const { url, init } = lastCall()
    expect(url).toBe("/api/items/item-1/batches/b1/consume")
    expect(init.method).toBe("POST")
    expect(init.body).toBe(JSON.stringify({ quantity: 1 }))
  })

  it("consumes via FEFO across batches", async () => {
    mockJson({ consumed: [{ batch_id: "b1", quantity: 2 }] })

    const result = await consumeFefo("item-1", { quantity: 2 }, "jwt")

    expect(result.consumed).toHaveLength(1)
    const { url, init } = lastCall()
    expect(url).toBe("/api/items/item-1/consume")
    expect(init.method).toBe("POST")
    expect(init.body).toBe(JSON.stringify({ quantity: 2 }))
  })

  it("disables batch tracking", async () => {
    mockJson({ id: "item-1", track_batches: false })

    const result = await disableBatches("item-1", "jwt")

    expect(result.track_batches).toBe(false)
    const { url, init } = lastCall()
    expect(url).toBe("/api/items/item-1/batches/disable")
    expect(init.method).toBe("POST")
  })
})
