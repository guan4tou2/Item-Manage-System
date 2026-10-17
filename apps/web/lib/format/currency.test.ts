import { describe, expect, it } from "vitest"

import {
  CURRENCIES,
  CURRENCY_SYMBOLS,
  formatCurrency,
} from "./currency"

describe("formatCurrency", () => {
  it("formats TWD with an NT$ prefix in zh-TW", () => {
    expect(formatCurrency("1200", "TWD", "zh-TW")).toBe("NT$1,200")
  })

  it("formats TWD with an NT$ prefix in en too", () => {
    expect(formatCurrency("1200", "TWD", "en")).toBe("NT$1,200")
  })

  it("keeps two decimals for fractional amounts", () => {
    expect(formatCurrency("99.50", "TWD", "zh-TW")).toBe("NT$99.50")
  })

  it("drops decimals for whole amounts", () => {
    expect(formatCurrency(2401, "TWD", "en")).toBe("NT$2,401")
    expect(formatCurrency("10.00", "TWD", "zh-TW")).toBe("NT$10")
  })

  it("uses zero decimals for JPY", () => {
    expect(formatCurrency("1200", "JPY", "zh-TW")).toBe("¥1,200")
    expect(formatCurrency("1200.4", "JPY", "en")).toBe("¥1,200")
  })

  it("formats the other whitelist currencies", () => {
    expect(formatCurrency("1200", "USD", "en")).toBe("US$1,200")
    expect(formatCurrency("1200", "EUR", "en")).toBe("€1,200")
    expect(formatCurrency("1200", "CNY", "en")).toBe("CN¥1,200")
    expect(formatCurrency("1200", "HKD", "en")).toBe("HK$1,200")
  })

  it("returns an em dash for missing or invalid values", () => {
    expect(formatCurrency(null, "TWD", "zh-TW")).toBe("—")
    expect(formatCurrency(undefined, "TWD", "zh-TW")).toBe("—")
    expect(formatCurrency("", "TWD", "zh-TW")).toBe("—")
    expect(formatCurrency("abc", "TWD", "zh-TW")).toBe("—")
    expect(formatCurrency(Number.NaN, "TWD", "zh-TW")).toBe("—")
  })

  it("falls back to Intl's own rendering for an unknown currency code", () => {
    expect(formatCurrency("1200", "XYZ", "en")).toBe("XYZ\u00a01,200")
  })

  it("exposes the whitelist and its symbols", () => {
    expect([...CURRENCIES]).toEqual(["TWD", "USD", "EUR", "JPY", "CNY", "HKD"])
    expect(CURRENCY_SYMBOLS.TWD).toBe("NT$")
    expect(CURRENCY_SYMBOLS.JPY).toBe("¥")
  })
})
