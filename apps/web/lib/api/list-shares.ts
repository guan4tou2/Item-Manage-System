import type { components } from "@ims/api-types"

import { apiFetch } from "./client"

export type ListShare = components["schemas"]["ListShareRead"]
export type ShareCreateBody = components["schemas"]["ListShareCreate"]
export type CreatedShare = components["schemas"]["ListShareCreated"]

export async function listShares(listId: string, accessToken: string | null): Promise<ListShare[]> {
  const res = await apiFetch(`/lists/${listId}/shares`, { accessToken })
  return res.json()
}

export async function createShare(listId: string, body: ShareCreateBody, accessToken: string | null): Promise<CreatedShare> {
  const res = await apiFetch(`/lists/${listId}/shares`, {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return res.json()
}

export async function revokeShare(listId: string, shareId: string, accessToken: string | null): Promise<void> {
  await apiFetch(`/lists/${listId}/shares/${shareId}`, { method: "DELETE", accessToken })
}
