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
        // 以位元組當 body：Node 22 的 fetch 會把 jsdom 的 Blob 當成 Blob-like 並呼叫其不存在的
        // stream()，導致 res.blob() 失敗（Node 24 不會），測試結果不應取決於 Node 版本。
        return new Response(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), {
          status: 200,
          headers: { "content-type": "image/png" },
        })
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
    // 不用 instanceof：res.blob() 回傳的是 Node 的 Blob，jsdom 環境的全域 Blob 可能是另一個類別
    expect(result.items[0]?.qrBlob.size).toBe(4)
    expect(result.items[0]?.qrBlob.type).toBe("image/png")
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
