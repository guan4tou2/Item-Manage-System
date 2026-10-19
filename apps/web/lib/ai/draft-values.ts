import type { DraftAcceptRequest, DraftRead } from "@/lib/api/ai-drafts"
import type { CategoryTreeNode } from "@/lib/api/categories"
import { findCategoryByName } from "@/components/categories/category-select"

/** 草稿卡的編輯值（送出前以 `acceptBodyFrom` 轉為 API payload）。 */
export interface DraftValues {
  name: string
  description: string
  categoryId: number | null
  locationId: number | null
  tags: string[]
  quantity: number
  cost: string
}

/** 目前值來自歷史建議的欄位（供「依歷史」徽章顯示）。 */
export interface HistorySource {
  category: { id: number; name: string } | null
  location: { id: number; name: string } | null
  tags: string[]
}

export const EMPTY_HISTORY: HistorySource = { category: null, location: null, tags: [] }

/**
 * 建議預設：分類／位置／標籤以本人歷史優先；
 * 歷史缺分類時退回 AI 建議的「完整同名分類」精確匹配；皆無則留空。
 *
 * 收據品項（Phase 33）：數量與成本帶入收據行（單價缺 → 成本留空可手動填）。
 */
export function seedDraftValues(
  draft: DraftRead,
  categories: CategoryTreeNode[],
): DraftValues {
  const ai = draft.payload.ai
  const history = draft.payload.history
  const suggestion = ai?.category_suggestion?.trim()
  const categoryId =
    history.category?.id ?? (suggestion ? findCategoryByName(categories, suggestion) : null)
  const receiptItem = draft.payload.receipt_item ?? null

  return {
    name: ai?.name ?? "",
    description: ai?.description ?? "",
    categoryId,
    locationId: history.location?.id ?? null,
    tags: history.tags.map((tag) => tag.name),
    quantity: receiptItem?.quantity ?? 1,
    cost: receiptItem?.unit_price ?? "",
  }
}

/** 由草稿 payload 取出歷史來源（徽章顯示用）。 */
export function seedDraftHistory(draft: DraftRead): HistorySource {
  const history = draft.payload.history
  return {
    category: history.category
      ? { id: history.category.id, name: history.category.name }
      : null,
    location: history.location
      ? { id: history.location.id, name: history.location.name }
      : null,
    tags: history.tags.map((tag) => tag.name),
  }
}

/** 編輯值 → accept payload：名稱去空白、description／cost 空字串轉 `null`。 */
export function acceptBodyFrom(values: DraftValues): DraftAcceptRequest {
  const description = values.description.trim()
  const cost = values.cost.trim()
  return {
    name: values.name.trim(),
    description: description === "" ? null : description,
    category_id: values.categoryId,
    location_id: values.locationId,
    tag_names: values.tags,
    quantity: values.quantity,
    cost: cost === "" ? null : cost,
  }
}

/**
 * 批量接受時的後備 payload：草稿尚未回報編輯值（極端情形）時，
 * 以與草稿卡相同的預設規則由 payload 重建。
 */
export function fallbackAcceptBody(
  draft: DraftRead,
  categories: CategoryTreeNode[],
): DraftAcceptRequest {
  return acceptBodyFrom(seedDraftValues(draft, categories))
}
