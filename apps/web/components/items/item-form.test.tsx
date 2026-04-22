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
})
