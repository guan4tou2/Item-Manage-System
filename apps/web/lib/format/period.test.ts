import { describe, expect, it } from "vitest"

import { formatPeriod } from "./period"

describe("formatPeriod", () => {
  it("formats a period in zh-TW", () => {
    expect(formatPeriod("2026-09", "zh-TW")).toBe("2026年9月")
  })

  it("formats a period in en", () => {
    expect(formatPeriod("2026-09", "en")).toBe("September 2026")
  })

  it("handles January without month drift", () => {
    expect(formatPeriod("2026-01", "en")).toBe("January 2026")
  })

  it("returns the raw value for invalid input", () => {
    expect(formatPeriod("nope", "en")).toBe("nope")
    expect(formatPeriod("2026-13", "en")).toBe("2026-13")
    expect(formatPeriod("", "en")).toBe("")
  })
})
