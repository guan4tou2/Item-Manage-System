import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type DraftRead =
  paths["/api/ai/drafts"]["get"]["responses"]["200"]["content"]["application/json"]["items"][number]

export type DraftListResponse =
  paths["/api/ai/drafts"]["get"]["responses"]["200"]["content"]["application/json"]

export type DraftCounts = DraftListResponse["counts"]

export type DraftStatus = DraftRead["status"]

export type DraftPayload = DraftRead["payload"]

export type DraftCreateResponse =
  paths["/api/ai/drafts"]["post"]["responses"]["201"]["content"]["application/json"]

export type DraftAcceptRequest =
  paths["/api/ai/drafts/{draft_id}/accept"]["post"]["requestBody"]["content"]["application/json"]

export type DraftAcceptResponse =
  paths["/api/ai/drafts/{draft_id}/accept"]["post"]["responses"]["200"]["content"]["application/json"]

export type DraftDiscardResponse =
  paths["/api/ai/drafts/discard"]["post"]["responses"]["200"]["content"]["application/json"]

export type ClassificationSuggestions =
  paths["/api/ai/suggest-classification"]["post"]["responses"]["200"]["content"]["application/json"]

/** 活動四態：佇列與計數的預設範圍（終態 accepted／discarded 不列預設清單）。 */
export const ACTIVE_DRAFT_STATUSES = ["pending", "processing", "ready", "failed"] as const

/** 待審核合計（入口卡徽章）：僅計活動四態。 */
export function activeDraftTotal(counts: DraftCounts): number {
  return ACTIVE_DRAFT_STATUSES.reduce((sum, status) => sum + counts[status], 0)
}

export async function createDrafts(
  imageIds: string[],
  accessToken: string | null,
): Promise<DraftCreateResponse> {
  const res = await apiFetch("/ai/drafts", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ image_ids: imageIds }),
  })
  return (await res.json()) as DraftCreateResponse
}

export async function listDrafts(
  params: { status?: DraftStatus; limit?: number; offset?: number } = {},
  accessToken: string | null,
): Promise<DraftListResponse> {
  const q = new URLSearchParams()
  if (params.status !== undefined) q.set("status", params.status)
  if (params.limit !== undefined) q.set("limit", String(params.limit))
  if (params.offset !== undefined) q.set("offset", String(params.offset))
  const suffix = q.size > 0 ? `?${q.toString()}` : ""
  const res = await apiFetch(`/ai/drafts${suffix}`, { accessToken })
  return (await res.json()) as DraftListResponse
}

export async function processDraft(
  id: string,
  accessToken: string | null,
): Promise<DraftRead> {
  const res = await apiFetch(`/ai/drafts/${id}/process`, { method: "POST", accessToken })
  return (await res.json()) as DraftRead
}

export async function acceptDraft(
  id: string,
  body: DraftAcceptRequest,
  accessToken: string | null,
): Promise<DraftAcceptResponse> {
  const res = await apiFetch(`/ai/drafts/${id}/accept`, {
    method: "POST",
    accessToken,
    body: JSON.stringify(body),
  })
  return (await res.json()) as DraftAcceptResponse
}

export async function discardDraft(
  id: string,
  accessToken: string | null,
): Promise<DraftRead> {
  const res = await apiFetch(`/ai/drafts/${id}/discard`, { method: "POST", accessToken })
  return (await res.json()) as DraftRead
}

export async function discardDrafts(
  ids: string[],
  accessToken: string | null,
): Promise<DraftDiscardResponse> {
  const res = await apiFetch("/ai/drafts/discard", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ ids }),
  })
  return (await res.json()) as DraftDiscardResponse
}

export async function suggestClassification(
  name: string,
  accessToken: string | null,
): Promise<ClassificationSuggestions> {
  const res = await apiFetch("/ai/suggest-classification", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ name }),
  })
  return (await res.json()) as ClassificationSuggestions
}
