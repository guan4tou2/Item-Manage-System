import type { ItemFormValues } from "@/components/items/item-form"
import { createBatch } from "@/lib/api/batches"
import { saveItemCustomValues, type CustomFieldRead } from "@/lib/api/customization"
import { createItem, type ItemCreate, type ItemRead } from "@/lib/api/items"
import { createBody } from "./steps"

export interface ItemSubmission {
  values: ItemFormValues
  trackBatches: boolean
  customFields: CustomFieldRead[]
}

/** 建立成功後的補充步驟失敗不可重建物品。 */
export async function submitItem(
  draft: ItemSubmission,
  key: string,
  token: string | null,
  create: (body: ItemCreate) => Promise<ItemRead> = (body) => createItem(body, token, key),
) {
  const { values } = draft
  const item = await create(createBody(values))
  let partial: "batch" | "custom" | null = null
  try {
    if (draft.trackBatches) {
      try {
        await createBatch(item.id, {}, token)
      } catch {
        return { item, partial: "batch" as const }
      }
    }
    await saveItemCustomValues(item.id, draft.customFields, values.custom_values, token)
  } catch {
    partial = "custom"
  }
  return { item, partial }
}
