import type { DraftRead } from "@/lib/api/ai-drafts"
import type { ReceiptSnapshot } from "@/lib/api/ai-receipts"

/** 佇列中的一個群組：一般照片草稿自成一群（`receiptId=null`），收據品項同組。 */
export interface DraftGroup {
  receiptId: string | null
  /** 收據中繼資料快照（照片草稿為 `null`；收據缺快照亦為 `null`）。 */
  snapshot: ReceiptSnapshot | null
  drafts: DraftRead[]
}

/** 取草稿的收據快照（照片草稿／舊資料缺鍵 → `null`）。 */
export function receiptSnapshotOf(draft: DraftRead): ReceiptSnapshot | null {
  return draft.payload.receipt ?? null
}

function lineIndex(draft: DraftRead): number {
  return draft.payload.receipt_item?.index ?? 0
}

/**
 * 佇列分組（Phase 33）：
 *
 * - 照片草稿維持原位、各自一群、無標頭
 * - 同 `receipt_id` 的草稿聚為一群，組內依收據行序（`receipt_item.index`）升冪
 * - 群的順序＝該群**第一列**在原始清單中的位置（清單本身 `created_at DESC`）
 * - 快照取群內第一個帶快照的草稿（同一收據各列快照相同）
 */
export function groupDrafts(drafts: DraftRead[]): DraftGroup[] {
  const groups: DraftGroup[] = []
  const byReceipt = new Map<string, DraftGroup>()

  for (const draft of drafts) {
    const receiptId = draft.receipt_id ?? null
    if (receiptId === null) {
      groups.push({ receiptId: null, snapshot: null, drafts: [draft] })
      continue
    }
    const existing = byReceipt.get(receiptId)
    if (existing) {
      existing.drafts.push(draft)
      existing.snapshot = existing.snapshot ?? receiptSnapshotOf(draft)
      continue
    }
    const group: DraftGroup = {
      receiptId,
      snapshot: receiptSnapshotOf(draft),
      drafts: [draft],
    }
    byReceipt.set(receiptId, group)
    groups.push(group)
  }

  for (const group of groups) {
    if (group.receiptId !== null) {
      group.drafts.sort((a, b) => lineIndex(a) - lineIndex(b))
    }
  }
  return groups
}

/**
 * 對帳：收據總額與品項合計是否相符（差額 < 0.01 視為相符）。
 *
 * 任一側缺值 → `false`（未知，由 UI 顯示「未標示總額」而非相符）。
 */
export function receiptTotalsMatch(
  total: string | null | undefined,
  itemTotal: string | null | undefined,
): boolean {
  if (total === null || total === undefined || itemTotal === null || itemTotal === undefined) {
    return false
  }
  const left = Number(total)
  const right = Number(itemTotal)
  if (!Number.isFinite(left) || !Number.isFinite(right)) return false
  return Math.abs(left - right) < 0.01
}
