import { afterEach, describe, expect, it, vi } from "vitest"

import { createRestockListFromLowStockItems } from "./lists"

const originalFetch = global.fetch

describe("lists api client", () => {
  afterEach(() => {
    global.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it("creates a shopping list with low-stock deficit entries", async () => {
    global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === "/api/lists") {
        return new Response(
          JSON.stringify({
            id: "list-1",
            kind: "shopping",
            title: "Restock 2026-06-23",
            description: null,
            start_date: null,
            end_date: null,
            budget: null,
            entry_count: 0,
            done_count: 0,
            created_at: "2026-06-23T00:00:00Z",
            updated_at: "2026-06-23T00:00:00Z",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        )
      }
      if (url === "/api/lists/list-1/entries") {
        return new Response(
          JSON.stringify({
            id: "entry-1",
            list_id: "list-1",
            name: JSON.parse(String(init?.body)).name,
            quantity: JSON.parse(String(init?.body)).quantity,
            note: null,
            price: null,
            link: JSON.parse(String(init?.body)).link,
            position: 0,
            is_done: false,
            created_at: "2026-06-23T00:00:00Z",
            updated_at: "2026-06-23T00:00:00Z",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        )
      }
      return new Response(null, { status: 404 })
    })

    const list = await createRestockListFromLowStockItems(
      [
        {
          item_id: "item-1",
          name: "Batteries",
          quantity: 1,
          min_quantity: 5,
          deficit: 4,
        },
      ],
      "jwt",
      { title: "Restock 2026-06-23" },
    )

    expect(list.id).toBe("list-1")
    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      "/api/lists",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          kind: "shopping",
          title: "Restock 2026-06-23",
          description: null,
        }),
      }),
    )
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      "/api/lists/list-1/entries",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          name: "Batteries",
          quantity: 4,
          link: "/items/item-1",
          is_done: false,
        }),
      }),
    )
  })
})
