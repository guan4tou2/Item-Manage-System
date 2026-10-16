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

  it("ignores non-numeric category and location", () => {
    const p = new URLSearchParams("category=abc&location=xyz")
    expect(filtersFromSearchParams(p)).toEqual({})
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

describe("location scope", () => {
  it("parses location_scope=exact from the URL", () => {
    const parsed = filtersFromSearchParams(new URLSearchParams("location=7&location_scope=exact"))
    expect(parsed.locationId).toBe(7)
    expect(parsed.locationScope).toBe("exact")
  })

  it("defaults to subtree when location_scope is absent", () => {
    const parsed = filtersFromSearchParams(new URLSearchParams("location=7"))
    expect(parsed.locationScope).toBeUndefined()
  })

  it("serialises the exact scope and keeps subtree implicit", () => {
    expect(
      filtersToSearchParams({ locationId: 7, locationScope: "exact" }).toString(),
    ).toBe("location=7&location_scope=exact")
    expect(filtersToSearchParams({ locationId: 7 }).toString()).toBe("location=7")
  })

  it("drops the scope param when there is no location filter", () => {
    expect(filtersToSearchParams({ locationScope: "exact" }).toString()).toBe("")
  })
})
