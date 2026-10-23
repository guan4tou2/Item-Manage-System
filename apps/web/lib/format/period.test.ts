import { describe, expect, it } from "vitest"

import { formatPeriod, formatPeriodRange } from "./period"

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

describe("formatPeriodRange", () => {
  it("formats a same-month range in zh-TW and en", () => {
    expect(formatPeriodRange("2026-10-12", "2026-10-18", "zh-TW")).toBe(
      "2026 年 10 月 12–18 日",
    )
    expect(formatPeriodRange("2026-10-12", "2026-10-18", "en")).toBe(
      "Oct 12–18, 2026",
    )
  })

  it("formats a cross-month range in the same year", () => {
    expect(formatPeriodRange("2025-09-29", "2025-10-05", "zh-TW")).toBe(
      "2025 年 9 月 29 日–10 月 5 日",
    )
    expect(formatPeriodRange("2025-09-29", "2025-10-05", "en")).toBe(
      "Sep 29–Oct 5, 2025",
    )
  })

  it("formats a cross-year range", () => {
    expect(formatPeriodRange("2025-12-29", "2026-01-04", "zh-TW")).toBe(
      "2025 年 12 月 29 日–2026 年 1 月 4 日",
    )
    expect(formatPeriodRange("2025-12-29", "2026-01-04", "en")).toBe(
      "Dec 29, 2025–Jan 4, 2026",
    )
  })

  it("returns the raw range for invalid input", () => {
    expect(formatPeriodRange("nope", "2026-10-18", "en")).toBe(
      "nope–2026-10-18",
    )
    expect(formatPeriodRange("2026-02-30", "2026-03-01", "en")).toBe(
      "2026-02-30–2026-03-01",
    )
  })
})
