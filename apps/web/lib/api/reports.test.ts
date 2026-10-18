import { afterEach, describe, expect, it, vi } from "vitest"

import { getReport, listReports } from "./reports"

const originalFetch = global.fetch

function jsonResponse(payload: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  })
}

const emptyList = { items: [], total: 0, limit: 20, offset: 0 }

describe("reports api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("lists reports with limit and offset", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) => jsonResponse(emptyList),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    const result = await listReports({ limit: 5, offset: 10 }, "jwt")

    expect(result).toEqual(emptyList)
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/reports?limit=5&offset=10")
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer jwt")
  })

  it("omits query when no params given", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) => jsonResponse(emptyList),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    await listReports({}, null)

    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/reports")
  })

  it("fetches a single report by id", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse({ id: "r1", period: "2026-09" }),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    const report = await getReport("r1", "jwt")

    expect(report.id).toBe("r1")
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/reports/r1")
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer jwt")
  })

  it("throws ApiError for a 404 report", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(JSON.stringify({ detail: "report not found" }), {
          status: 404,
          headers: { "content-type": "application/json" },
        }),
    )
    global.fetch = fetchMock as unknown as typeof global.fetch

    await expect(getReport("missing", "jwt")).rejects.toMatchObject({
      status: 404,
    })
  })
})
