import { describe, expect, it } from "vitest"

import type { DraftRead } from "@/lib/api/ai-drafts"
import type { CategoryTreeNode } from "@/lib/api/categories"

import {
  acceptBodyFrom,
  fallbackAcceptBody,
  seedDraftHistory,
  seedDraftValues,
} from "./draft-values"

const categories: CategoryTreeNode[] = [
  {
    id: 3,
    name: "Kitchen",
    parent_id: null,
    children: [{ id: 4, name: "Mugs", parent_id: 3, children: [] }],
  },
]

function draft(payload: DraftRead["payload"]): DraftRead {
  return {
    id: "draft-1",
    source: "batch_photo",
    status: "ready",
    image_id: "img-1",
    item_id: null,
    error_code: null,
    payload,
    processed_at: "2026-10-19T02:11:09Z",
    created_at: "2026-10-19T02:11:03Z",
  }
}

describe("seedDraftValues", () => {
  it("prefers history over the AI suggestion", () => {
    const values = seedDraftValues(
      draft({
        version: 1,
        ai: {
          name: "Coffee dripper",
          description: null,
          category_suggestion: "Mugs",
          tag_suggestions: ["coffee"],
        },
        history: {
          category: { id: 3, name: "Kitchen", item_count: 12, score: 4 },
          location: { id: 7, name: "Shelf", item_count: 2, score: 1 },
          tags: [{ name: "coffee", item_count: 6, score: 3 }],
        },
      }),
      categories,
    )

    expect(values).toEqual({
      name: "Coffee dripper",
      description: "",
      categoryId: 3,
      locationId: 7,
      tags: ["coffee"],
      quantity: 1,
      cost: "",
    })
  })

  it("matches the AI category suggestion by full name when history is empty", () => {
    const values = seedDraftValues(
      draft({
        version: 1,
        ai: {
          name: "Mug",
          description: "Ceramic",
          category_suggestion: "Mugs",
          tag_suggestions: [],
        },
        history: { category: null, location: null, tags: [] },
      }),
      categories,
    )

    expect(values.categoryId).toBe(4)
  })

  it("leaves everything empty when neither source suggests anything", () => {
    const values = seedDraftValues(
      draft({ version: 1, ai: null, history: { category: null, location: null, tags: [] } }),
      categories,
    )

    expect(values).toMatchObject({ name: "", description: "", categoryId: null, tags: [] })
  })
})

describe("seedDraftHistory", () => {
  it("mirrors the payload history for the badges", () => {
    const history = seedDraftHistory(
      draft({
        version: 1,
        ai: null,
        history: {
          category: { id: 9, name: "Storage", item_count: 4, score: 2 },
          location: null,
          tags: [{ name: "tea", item_count: 2, score: 1 }],
        },
      }),
    )

    expect(history).toEqual({
      category: { id: 9, name: "Storage" },
      location: null,
      tags: ["tea"],
    })
  })
})

describe("acceptBodyFrom", () => {
  it("trims the name and nulls blank optional fields", () => {
    expect(
      acceptBodyFrom({
        name: "  V60 dripper  ",
        description: "   ",
        categoryId: null,
        locationId: null,
        tags: [],
        quantity: 2,
        cost: "",
      }),
    ).toEqual({
      name: "V60 dripper",
      description: null,
      category_id: null,
      location_id: null,
      tag_names: [],
      quantity: 2,
      cost: null,
    })
  })

  it("keeps filled description and cost", () => {
    expect(
      acceptBodyFrom({
        name: "Mug",
        description: "Ceramic",
        categoryId: 4,
        locationId: 7,
        tags: ["coffee"],
        quantity: 1,
        cost: "450",
      }),
    ).toEqual({
      name: "Mug",
      description: "Ceramic",
      category_id: 4,
      location_id: 7,
      tag_names: ["coffee"],
      quantity: 1,
      cost: "450",
    })
  })
})

describe("fallbackAcceptBody", () => {
  it("rebuilds a payload from the draft when nothing was reported", () => {
    const body = fallbackAcceptBody(
      draft({
        version: 1,
        ai: {
          name: "Mug",
          description: null,
          category_suggestion: "Mugs",
          tag_suggestions: [],
        },
        history: { category: null, location: null, tags: [] },
      }),
      categories,
    )

    expect(body).toMatchObject({ name: "Mug", category_id: 4, quantity: 1, cost: null })
  })
})
