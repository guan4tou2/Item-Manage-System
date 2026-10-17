import { describe, expect, it } from "vitest"

import { itemCostPayload } from "./cost"

describe("itemCostPayload", () => {
  it("maps blank input to null", () => {
    expect(itemCostPayload("")).toBeNull()
    expect(itemCostPayload("   ")).toBeNull()
    expect(itemCostPayload(undefined)).toBeNull()
    expect(itemCostPayload(null)).toBeNull()
  })

  it("trims and passes through valid decimal strings", () => {
    expect(itemCostPayload("1200.50")).toBe("1200.50")
    expect(itemCostPayload(" 12.30 ")).toBe("12.30")
    expect(itemCostPayload("0")).toBe("0")
  })
})
