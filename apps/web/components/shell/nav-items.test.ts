import { describe, expect, it } from "vitest"

import { NAV_GROUPS, NAV_ITEMS, STATS_MENU_ITEMS } from "./nav-items"

describe("nav-items", () => {
  it("keeps eleven first-level entries", () => {
    expect(NAV_ITEMS).toHaveLength(11)
  })

  it("puts statistics and reports in the statistics menu", () => {
    expect(STATS_MENU_ITEMS.map((item) => item.href)).toEqual([
      "/statistics",
      "/reports",
    ])
  })

  it("covers every first-level entry exactly once across the four groups", () => {
    expect(NAV_GROUPS.map((group) => group.id)).toEqual([
      "inventory",
      "analysis",
      "collab",
      "system",
    ])

    const grouped = NAV_GROUPS.flatMap((group) => group.items.map((item) => item.key))
    const expected = NAV_ITEMS.map((item) => item.key)
    expect([...grouped].sort()).toEqual([...expected, "reports"].sort())
    expect(new Set(grouped).size).toBe(grouped.length)
  })
})
