import { describe, expect, it } from "vitest"

import { canonicalizeBarcode, isBarcodeLike } from "./barcode"

describe("canonicalizeBarcode", () => {
  it("strips whitespace and hyphens from numeric codes", () => {
    expect(canonicalizeBarcode(" 4710085200016 ")).toBe("4710085200016")
    expect(canonicalizeBarcode("978-0-306-40615-7")).toBe("9780306406157")
  })

  it("uppercases the ISBN-10 check digit", () => {
    expect(canonicalizeBarcode("0-8044-2957-x")).toBe("080442957X")
  })

  it("keeps alphanumeric SKUs as trimmed originals", () => {
    expect(canonicalizeBarcode(" ABC-123 ")).toBe("ABC-123")
    expect(canonicalizeBarcode("SKU_99")).toBe("SKU_99")
  })

  it("returns empty string for empty input", () => {
    expect(canonicalizeBarcode("   ")).toBe("")
    expect(canonicalizeBarcode(null)).toBe("")
    expect(canonicalizeBarcode(undefined)).toBe("")
  })
})

describe("isBarcodeLike", () => {
  it("accepts EAN/UPC/ISBN-like payloads", () => {
    expect(isBarcodeLike("4710085200016")).toBe(true)
    expect(isBarcodeLike("96385074")).toBe(true)
    expect(isBarcodeLike("978-0-306-40615-7")).toBe(true)
    expect(isBarcodeLike("080442957X")).toBe(true)
    expect(isBarcodeLike("080442957x")).toBe(true)
  })

  it("rejects non-barcode payloads", () => {
    expect(isBarcodeLike("hello world")).toBe(false)
    expect(isBarcodeLike("12345")).toBe(false)
    expect(isBarcodeLike("SKU_99")).toBe(false)
    expect(isBarcodeLike("")).toBe(false)
  })
})
