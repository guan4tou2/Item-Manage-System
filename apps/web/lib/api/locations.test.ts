import { afterEach, describe, expect, it, vi } from "vitest"

import {
  createLocation,
  deleteLocation,
  getLocationPath,
  getLocationTree,
  listLocations,
  moveLocation,
  reorderLocations,
} from "./locations"

const originalFetch = global.fetch

function mockFetch(payload: unknown = {}) {
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  )
  global.fetch = fetchMock as unknown as typeof global.fetch
  return fetchMock
}

describe("locations api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("lists locations from the flat endpoint", async () => {
    const fetchMock = mockFetch([])
    await listLocations("jwt")
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/locations")
  })

  it("fetches the nested tree", async () => {
    const fetchMock = mockFetch([])
    await getLocationTree("jwt")
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/locations/tree")
  })

  it("fetches a node breadcrumb path", async () => {
    const fetchMock = mockFetch({ id: 3, path: "1F / 廚房", nodes: [] })
    await getLocationPath(3, "jwt")
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/locations/3/path")
  })

  it("creates a child node with parent_id", async () => {
    const fetchMock = mockFetch({})
    await createLocation({ name: "廚房", parent_id: 1, kind: "room" }, "jwt")
    const init = fetchMock.mock.calls[0]?.[1]
    expect(init?.method).toBe("POST")
    expect(JSON.parse(String(init?.body))).toEqual({
      name: "廚房",
      parent_id: 1,
      kind: "room",
    })
  })

  it("moves a node by patching parent_id (null → root)", async () => {
    const fetchMock = mockFetch({})
    await moveLocation(7, null, "jwt")
    const init = fetchMock.mock.calls[0]?.[1]
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/locations/7")
    expect(init?.method).toBe("PATCH")
    expect(JSON.parse(String(init?.body))).toEqual({ parent_id: null })
  })

  it("reorders siblings with parent scope", async () => {
    const fetchMock = mockFetch([])
    await reorderLocations({ parent_id: 2, location_ids: [5, 4] }, "jwt")
    const init = fetchMock.mock.calls[0]?.[1]
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/locations/reorder")
    expect(JSON.parse(String(init?.body))).toEqual({
      parent_id: 2,
      location_ids: [5, 4],
    })
  })

  it("surfaces structured 409 detail on delete", async () => {
    global.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({ detail: { code: "has_items", items: 3, children: 0 } }),
        { status: 409, headers: { "content-type": "application/json" } },
      ),
    ) as unknown as typeof global.fetch

    await expect(deleteLocation(9, "jwt")).rejects.toMatchObject({
      status: 409,
      body: { detail: { code: "has_items", items: 3, children: 0 } },
    })
  })
})
