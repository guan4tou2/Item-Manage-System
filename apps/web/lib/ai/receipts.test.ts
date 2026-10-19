import { describe, expect, it } from "vitest"

import type { DraftRead } from "@/lib/api/ai-drafts"

import { groupDrafts, receiptSnapshotOf, receiptTotalsMatch } from "./receipts"

function draft(overrides: Partial<DraftRead> & { id: string }): DraftRead {
  return {
    source: "batch_photo",
    status: "ready",
    image_id: null,
    item_id: null,
    error_code: null,
    payload: {
      version: 1,
      ai: null,
      history: { category: null, location: null, tags: [] },
    },
    processed_at: null,
    created_at: "2026-10-19T02:11:03Z",
    receipt_id: null,
    ...overrides,
  } as DraftRead
}

function receiptDraft(
  id: string,
  receiptId: string,
  index: number,
  overrides: Partial<DraftRead> = {},
): DraftRead {
  return draft({
    id,
    source: "receipt",
    receipt_id: receiptId,
    payload: {
      version: 1,
      ai: { name: `品項${index}`, description: null, category_suggestion: null, tag_suggestions: [] },
      history: { category: null, location: null, tags: [] },
      receipt: {
        merchant: "全聯",
        purchased_at: "2026-10-18",
        currency: "TWD",
        total: "300.00",
        item_total: "300.00",
        discrepancy: "0.00",
        page_count: 2,
        truncated: false,
      },
      receipt_item: {
        index,
        quantity: 1,
        unit_price: "100.00",
        subtotal: "100.00",
      },
    },
    ...overrides,
  })
}

describe("groupDrafts", () => {
  it("returns an empty list for no drafts", () => {
    expect(groupDrafts([])).toEqual([])
  })

  it("keeps photo drafts in place without a group header", () => {
    const photo = draft({ id: "p1" })

    const groups = groupDrafts([photo])

    expect(groups).toEqual([{ receiptId: null, snapshot: null, drafts: [photo] }])
  })

  it("groups receipt drafts and orders items by receipt line index", () => {
    const first = receiptDraft("r1", "receipt-a", 0)
    const second = receiptDraft("r2", "receipt-a", 1)
    const third = receiptDraft("r3", "receipt-a", 2)

    const groups = groupDrafts([third, first, second])

    expect(groups).toHaveLength(1)
    expect(groups[0]!.receiptId).toBe("receipt-a")
    expect(groups[0]!.drafts.map((item) => item.id)).toEqual(["r1", "r2", "r3"])
  })

  it("keeps mixed photo and receipt drafts in their original order", () => {
    const photoA = draft({ id: "p1" })
    const receipt1 = receiptDraft("r1", "receipt-a", 0)
    const photoB = draft({ id: "p2" })
    const receipt2 = receiptDraft("r2", "receipt-b", 0)

    const groups = groupDrafts([photoA, receipt1, photoB, receipt2])

    expect(groups.map((group) => group.receiptId)).toEqual([
      null,
      "receipt-a",
      null,
      "receipt-b",
    ])
    expect(groups[1]!.drafts[0]!.id).toBe("r1")
  })

  it("merges non-adjacent drafts of the same receipt at the first position", () => {
    const receipt1 = receiptDraft("r1", "receipt-a", 0)
    const photo = draft({ id: "p1" })
    const receipt2 = receiptDraft("r2", "receipt-a", 1)

    const groups = groupDrafts([receipt1, photo, receipt2])

    expect(groups).toHaveLength(2)
    expect(groups[0]!.receiptId).toBe("receipt-a")
    expect(groups[0]!.drafts.map((item) => item.id)).toEqual(["r1", "r2"])
    expect(groups[1]!.receiptId).toBeNull()
  })

  it("takes the snapshot from the first draft of the group", () => {
    const withSnapshot = receiptDraft("r1", "receipt-a", 0)
    const withoutSnapshot = receiptDraft("r2", "receipt-a", 1)
    withoutSnapshot.payload = {
      version: 1,
      ai: withoutSnapshot.payload.ai,
      history: withoutSnapshot.payload.history,
    }

    const groups = groupDrafts([withoutSnapshot, withSnapshot])

    expect(groups[0]!.snapshot?.merchant).toBe("全聯")
    expect(groups[0]!.snapshot?.page_count).toBe(2)
  })

  it("returns a null snapshot when no draft carries receipt metadata", () => {
    const first = receiptDraft("r1", "receipt-a", 0)
    const second = receiptDraft("r2", "receipt-a", 1)
    for (const item of [first, second]) {
      item.payload = {
        version: 1,
        ai: item.payload.ai,
        history: item.payload.history,
      }
    }

    const groups = groupDrafts([first, second])

    expect(groups[0]!.snapshot).toBeNull()
  })
})

describe("receiptTotalsMatch", () => {
  it("matches when the difference is below one cent", () => {
    expect(receiptTotalsMatch("100.00", "100.00")).toBe(true)
    expect(receiptTotalsMatch("100.00", "100.004")).toBe(true)
  })

  it("reports a mismatch for real differences", () => {
    expect(receiptTotalsMatch("100.00", "99.99")).toBe(false)
    expect(receiptTotalsMatch("100.00", "101.00")).toBe(false)
  })

  it("is unknown when either side is missing", () => {
    expect(receiptTotalsMatch(null, "100.00")).toBe(false)
    expect(receiptTotalsMatch("100.00", null)).toBe(false)
    expect(receiptTotalsMatch(undefined, undefined)).toBe(false)
  })
})

describe("receiptSnapshotOf", () => {
  it("reads the snapshot from a receipt draft", () => {
    const snapshot = receiptSnapshotOf(receiptDraft("r1", "receipt-a", 0))

    expect(snapshot).toMatchObject({ merchant: "全聯", currency: "TWD" })
  })

  it("returns null for photo drafts", () => {
    expect(receiptSnapshotOf(draft({ id: "p1" }))).toBeNull()
  })
})
