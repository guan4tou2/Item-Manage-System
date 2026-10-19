import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type SearchResponse =
  paths["/api/ai/search"]["post"]["responses"]["200"]["content"]["application/json"]

export type AppliedFilters = SearchResponse["applied"]

export type AppliedBucket = NonNullable<AppliedFilters["location"]>

export type SearchFallbackReason = NonNullable<SearchResponse["fallback_reason"]>

export type AskResponse =
  paths["/api/ai/ask"]["post"]["responses"]["200"]["content"]["application/json"]

export type Citation = AskResponse["citations"][number]

/**
 * 自然語言搜尋（Phase 34）。
 *
 * LLM 不可用時伺服器仍回 200（`fallback_reason` 說明原因、結果為關鍵字搜尋）；
 * 只有未開啟資料分享（`ai_opt_in_required`）等情況會以錯誤回應。
 */
export async function aiSearch(
  query: string,
  accessToken: string | null,
): Promise<SearchResponse> {
  const res = await apiFetch("/ai/search", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ query }),
  })
  return (await res.json()) as SearchResponse
}

/** 物品問答：以目前結果（或指定物品）為上下文，回答附引用。 */
export async function askItems(
  question: string,
  itemIds: string[],
  accessToken: string | null,
): Promise<AskResponse> {
  const res = await apiFetch("/ai/ask", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ question, item_ids: itemIds }),
  })
  return (await res.json()) as AskResponse
}
