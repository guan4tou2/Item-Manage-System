import { afterEach, describe, expect, it, vi } from "vitest"

import { bulkDeleteItems, bulkUpdateItems } from "./items"

const originalFetch = global.fetch

function mockJson(body: unknown, status = 200) {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  )
}

describe("items api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("bulk updates items with the expected payload", async () => {
    mockJson({ updated: 2, deleted: 0 })

    const result = await bulkUpdateItems(
      {
        item_ids: ["item-1", "item-2"],
        location_id: 3,
        tag_names: ["packed"],
        tag_mode: "replace",
      },
      "jwt",
    )

    expect(result.updated).toBe(2)
    expect(global.fetch).toHaveBeenLastCalledWith(
      "/api/items/bulk",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          item_ids: ["item-1", "item-2"],
          location_id: 3,
          tag_names: ["packed"],
          tag_mode: "replace",
        }),
        credentials: "include",
      }),
    )
  })

  it("bulk deletes items with the expected payload", async () => {
    mockJson({ updated: 0, deleted: 2 })

    const result = await bulkDeleteItems({ item_ids: ["item-1", "item-2"] }, "jwt")

    expect(result.deleted).toBe(2)
    expect(global.fetch).toHaveBeenLastCalledWith(
      "/api/items/bulk-delete",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ item_ids: ["item-1", "item-2"] }),
        credentials: "include",
      }),
    )
  })
})
