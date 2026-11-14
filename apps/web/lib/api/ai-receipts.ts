import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"
import type { DraftRead } from "./ai-drafts"

export type ReceiptCreateResponse =
  paths["/api/ai/receipts"]["post"]["responses"]["201"]["content"]["application/json"]

export type ReceiptSnapshot = NonNullable<
  DraftRead["payload"]["receipt"]
>

export type ReceiptItemSnapshot = NonNullable<
  DraftRead["payload"]["receipt_item"]
>

/**
 * 多頁收據 → 每個品項一列 `ready` 草稿（Phase 33）。
 *
 * 失敗時以 `detail` 回代碼字串（`ai_disabled`／`quota_exhausted`／
 * `upstream_error`／`no_items`），由呼叫端對照 `ai.receipts.errors.*`。
 */
export async function createReceipt(
  imageIds: string[],
  accessToken: string | null,
): Promise<ReceiptCreateResponse> {
  const res = await apiFetch("/ai/receipts", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ image_ids: imageIds }),
  })
  return (await res.json()) as ReceiptCreateResponse
}

export type ReceiptRead =
  paths["/api/ai/receipts/{receipt_id}"]["get"]["responses"]["200"]["content"]["application/json"]
export type ReceiptReview = NonNullable<ReceiptRead["review"]>

/** 讀取同張收據的所有草稿行，包含已處理的行。 */
export async function getReceipt(id: string, accessToken: string | null): Promise<ReceiptRead> {
  const res = await apiFetch(`/ai/receipts/${id}`, { accessToken })
  return (await res.json()) as ReceiptRead
}

export async function putReceiptReview(
  id: string, note: string | null, accessToken: string | null,
): Promise<ReceiptReview> {
  const res = await apiFetch(`/ai/receipts/${id}/review`, {
    method: "PUT", accessToken, body: JSON.stringify({ note }),
  })
  return (await res.json()) as ReceiptReview
}

export async function deleteReceiptReview(id: string, accessToken: string | null): Promise<void> {
  await apiFetch(`/ai/receipts/${id}/review`, { method: "DELETE", accessToken })
}
