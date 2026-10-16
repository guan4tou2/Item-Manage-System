import { afterEach, describe, expect, it, vi } from "vitest"

import { lookupBarcode } from "./barcodes"

const originalFetch = global.fetch

const payload = {
  code: "4710085200016",
  local_matches: [
    {
      id: "item-1",
      name: "牛奶",
      quantity: 2,
      image_id: null,
      location_path: "1F / 廚房 / 上櫃",
    },
  ],
  external: null,
  external_status: "skipped",
  cached: false,
}

describe("barcodes api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("requests the canonical code and returns the payload", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL) =>
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    const result = await lookupBarcode("4710085200016", "jwt")

    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/barcodes/4710085200016")
    expect(result.external_status).toBe("skipped")
    expect(result.local_matches[0]?.name).toBe("牛奶")
  })

  it("url-encodes codes with special characters", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL) =>
      new Response(JSON.stringify({ ...payload, local_matches: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    await lookupBarcode("ABC 123", "jwt")

    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/barcodes/ABC%20123")
  })

  it("throws an ApiError on non-2xx responses", async () => {
    global.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ detail: "invalid barcode" }), {
        status: 422,
        headers: { "content-type": "application/json" },
      }),
    ) as unknown as typeof global.fetch

    await expect(lookupBarcode("", "jwt")).rejects.toMatchObject({ status: 422 })
  })
})
