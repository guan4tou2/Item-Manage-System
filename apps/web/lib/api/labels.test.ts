import { afterEach, describe, expect, it, vi } from "vitest"

import { getBulkItemLabelBundles, getItemLabelsPdf } from "./labels"

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

  it("requests the PDF with repeated ids and parses the filename", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(new Uint8Array([0x25, 0x50, 0x44, 0x46]), {
        status: 200,
        headers: {
          "content-type": "application/pdf",
          "content-disposition": 'attachment; filename="item-labels-20261023.pdf"',
        },
      }),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    const result = await getItemLabelsPdf(["item-1", "item-2", "item-1"], "jwt")

    const [input, init] = fetchMock.mock.calls[0] as unknown as [
      RequestInfo | URL,
      RequestInit,
    ]
    expect(String(input)).toBe("/api/items/labels.pdf?ids=item-1&ids=item-2")
    expect((init.headers as Headers).get("authorization")).toBe("Bearer jwt")
    expect(result.filename).toBe("item-labels-20261023.pdf")
    expect(await result.blob.text()).toBe("%PDF")
  })

  it("falls back to a stable filename when the header is absent", async () => {
    global.fetch = vi.fn(async () =>
      new Response(new Uint8Array([0x25, 0x50, 0x44, 0x46]), {
        status: 200,
        headers: { "content-type": "application/pdf" },
      }),
    ) as unknown as typeof global.fetch

    const result = await getItemLabelsPdf(["item-1"], "jwt")

    expect(result.filename).toBe("item-labels.pdf")
  })
})
