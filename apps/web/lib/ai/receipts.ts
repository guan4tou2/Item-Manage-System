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

/** 收據對帳狀態（Phase 38；與 API 的 `balance_status` 對齊）。 */
export type ReceiptBalanceStatus =
  | "balanced"
  | "discrepancy"
  | "incomplete"
  | "unknown"

/** 收據對帳視圖（新版快照優先；舊快照退回舊判讀）。 */
export interface ReceiptBalanceView {
  status: ReceiptBalanceStatus
  /** 是否為含算術證據的新版快照（`balance_status` 存在）。 */
  evidence: boolean
  /** 算術值（Σ品項小計 − 折扣 + 稅 + 運費）。 */
  calculatedTotal: string | null
  /** 差額（收據總額 − 算術值）。 */
  discrepancy: string | null
  discount: string | null
  tax: string | null
  shipping: string | null
  /** 缺價（無法計算金額）的品項數。 */
  missingPriceCount: number
  /** AI 自述讀不確定的欄位數。 */
  uncertainCount: number
  /** 幣別未知（`XXX`）。 */
  currencyUnknown: boolean
}

/**
 * 收據對帳視圖（Phase 38 D3/D7）。
 *
 * - 新版快照（含 `balance_status`）→ 直接採信伺服器判讀與算術欄位
 * - 舊快照（無 `balance_status`）→ 沿用 Phase 33 的「總額 vs 品項合計」判讀，
 *   且 `evidence=false` → UI 不呈現算術拆解（避免舊資料被誤讀）
 */
export function receiptBalanceOf(
  snapshot: ReceiptSnapshot | null,
): ReceiptBalanceView {
  const empty: ReceiptBalanceView = {
    status: "unknown",
    evidence: false,
    calculatedTotal: null,
    discrepancy: null,
    discount: null,
    tax: null,
    shipping: null,
    missingPriceCount: 0,
    uncertainCount: 0,
    currencyUnknown: false,
  }
  if (!snapshot) return empty

  const currency = (snapshot.currency ?? "").toUpperCase()
  const currencyUnknown = currency === "" || currency === "XXX"
  const status = snapshot.balance_status ?? null

  if (status === null) {
    // 舊快照：總額 vs 品項合計
    if (!snapshot.total) {
      return { ...empty, status: "unknown", currencyUnknown }
    }
    const matched = receiptTotalsMatch(snapshot.total, snapshot.item_total)
    return {
      ...empty,
      status: matched ? "balanced" : "discrepancy",
      discrepancy: snapshot.discrepancy ?? null,
      currencyUnknown,
    }
  }

  return {
    status,
    evidence: true,
    calculatedTotal: snapshot.calculated_total ?? null,
    discrepancy: snapshot.discrepancy ?? null,
    discount: snapshot.discount ?? null,
    tax: snapshot.tax ?? null,
    shipping: snapshot.shipping ?? null,
    missingPriceCount: snapshot.missing_price_count ?? 0,
    uncertainCount: (snapshot.uncertain_fields ?? []).length,
    currencyUnknown,
  }
}
