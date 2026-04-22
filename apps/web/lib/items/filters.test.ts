import { describe, it, expect } from "vitest"
import { filtersFromSearchParams, filtersToSearchParams } from "./filters"

describe("filtersFromSearchParams", () => {
  it("parses all filters", () => {
    const p = new URLSearchParams("q=apple&category=1&location=2&tags=3,4&page=5")
    expect(filtersFromSearchParams(p)).toEqual({
      q: "apple", categoryId: 1, locationId: 2, tagIds: [3, 4], page: 5,
    })
  })

  it("returns empty object when nothing set", () => {
    expect(filtersFromSearchParams(new URLSearchParams())).toEqual({})
  })

  it("ignores invalid tag ids", () => {
    const p = new URLSearchParams("tags=1,abc,,2")
    expect(filtersFromSearchParams(p).tagIds).toEqual([1, 2])
  })

  it("coerces page below 1 to 1", () => {
    const p = new URLSearchParams("page=0")
    expect(filtersFromSearchParams(p).page).toBe(1)
  })
})

describe("filtersToSearchParams", () => {
  it("round-trips", () => {
    const f = { q: "a", categoryId: 1, locationId: 2, tagIds: [3, 4], page: 2 }
    const p = filtersToSearchParams(f)
    expect(Object.fromEntries(p.entries())).toEqual({
      q: "a", category: "1", location: "2", tags: "3,4", page: "2",
    })
  })

  it("omits page=1", () => {
    expect(filtersToSearchParams({ page: 1 }).toString()).toBe("")
  })

  it("omits empty tag list", () => {
    expect(filtersToSearchParams({ tagIds: [] }).toString()).toBe("")
  })
})
