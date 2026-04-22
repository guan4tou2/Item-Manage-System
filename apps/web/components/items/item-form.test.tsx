import { describe, it, expect } from "vitest"
import { itemFormSchema } from "./item-form"

describe("itemFormSchema", () => {
  const ok = {
    name: "thing", description: "", category_id: null, location_id: null,
    quantity: 1, notes: "", tag_names: [],
  }

  it("accepts a valid minimal record", () => {
    expect(itemFormSchema.safeParse(ok).success).toBe(true)
  })

  it("rejects empty name", () => {
    const r = itemFormSchema.safeParse({ ...ok, name: "" })
    expect(r.success).toBe(false)
  })

  it("rejects negative quantity", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: -1 })
    expect(r.success).toBe(false)
  })

  it("rejects non-integer quantity", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: 1.5 })
    expect(r.success).toBe(false)
  })

  it("rejects name over 200 chars with nameMax message", () => {
    const r = itemFormSchema.safeParse({ ...ok, name: "a".repeat(201) })
    expect(r.success).toBe(false)
    if (!r.success) expect(r.error.issues[0]?.message).toBe("nameMax")
  })

  it("reports nameRequired for empty name", () => {
    const r = itemFormSchema.safeParse({ ...ok, name: "" })
    if (!r.success) expect(r.error.issues[0]?.message).toBe("nameRequired")
  })

  it("reports quantityMin for negative", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: -1 })
    if (!r.success) expect(r.error.issues[0]?.message).toBe("quantityMin")
  })

  it("reports quantityInteger for non-integer", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: 1.5 })
    if (!r.success) expect(r.error.issues[0]?.message).toBe("quantityInteger")
  })

  it("accepts numeric string for quantity via coercion", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: "5" as unknown as number })
    expect(r.success).toBe(true)
  })
})
