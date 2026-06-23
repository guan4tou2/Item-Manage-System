import { afterEach, describe, expect, it, vi } from "vitest"

import { getBulkItemLabelBundles } from "./labels"

const originalFetch = global.fetch

describe("labels api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("fetches labels and QR blobs while skipping failed item IDs", async () => {
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === "/api/items/item-1/label") {
        return new Response(
          JSON.stringify({
            item_id: "item-1",
            name: "Router",
            quantity: 2,
            deep_link: "https://example.test/items/item-1",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        )
      }
      if (url === "/api/items/item-1/qr.png") {
        return new Response(new Blob(["png"], { type: "image/png" }), { status: 200 })
      }
      return new Response(JSON.stringify({ detail: "not found" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      })
    })

    const result = await getBulkItemLabelBundles(["item-1", "missing"], "jwt")

    expect(result.skippedCount).toBe(1)
    expect(result.items).toHaveLength(1)
    expect(result.items[0]?.itemId).toBe("item-1")
    expect(result.items[0]?.label.name).toBe("Router")
    expect(result.items[0]?.qrBlob).toBeInstanceOf(Blob)
  })
})
