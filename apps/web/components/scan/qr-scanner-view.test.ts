import { describe, expect, it } from "vitest"

import { extractItemIdFromPayload } from "./qr-scanner-view"

const VALID_UUID = "a1b2c3d4-e5f6-4a7b-8c9d-0123456789ab"

describe("extractItemIdFromPayload", () => {
  it("extracts UUID from a /items/{id} URL", () => {
    expect(
      extractItemIdFromPayload(`https://example.com/items/${VALID_UUID}`),
    ).toBe(VALID_UUID)
  })

  it("extracts UUID from a nested /items/{id} URL", () => {
    expect(
      extractItemIdFromPayload(
        `https://example.com/locale/en/items/${VALID_UUID}?ref=label`,
      ),
    ).toBe(VALID_UUID)
  })

  it("accepts a bare UUID as payload", () => {
    expect(extractItemIdFromPayload(VALID_UUID)).toBe(VALID_UUID)
  })

  it("lowercases the UUID for consistency", () => {
    const upper = VALID_UUID.toUpperCase()
    expect(extractItemIdFromPayload(upper)).toBe(VALID_UUID)
  })

  it("trims whitespace before parsing", () => {
    expect(extractItemIdFromPayload(`  ${VALID_UUID}  `)).toBe(VALID_UUID)
  })

  it("returns null for a non-items URL", () => {
    expect(
      extractItemIdFromPayload("https://example.com/users/abc"),
    ).toBeNull()
  })

  it("returns null for a URL without a UUID under /items", () => {
    expect(
      extractItemIdFromPayload("https://example.com/items/not-a-uuid"),
    ).toBeNull()
  })

  it("returns null for arbitrary text", () => {
    expect(extractItemIdFromPayload("hello world")).toBeNull()
  })

  it("returns null for an empty payload", () => {
    expect(extractItemIdFromPayload("")).toBeNull()
  })
})
