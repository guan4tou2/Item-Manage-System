import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type ListKind = "travel" | "shopping" | "collection" | "generic"

export type ListSummary =
  paths["/api/lists"]["get"]["responses"]["200"]["content"]["application/json"]["items"][number]

export type ListListResponse =
  paths["/api/lists"]["get"]["responses"]["200"]["content"]["application/json"]

export type ListDetail =
  paths["/api/lists/{list_id}"]["get"]["responses"]["200"]["content"]["application/json"]

export type ListEntry = ListDetail["entries"][number]

export type ListCreateBody =
  paths["/api/lists"]["post"]["requestBody"]["content"]["application/json"]

export type ListUpdateBody =
  paths["/api/lists/{list_id}"]["patch"]["requestBody"]["content"]["application/json"]

export type EntryCreateBody =
  paths["/api/lists/{list_id}/entries"]["post"]["requestBody"]["content"]["application/json"]

export type EntryUpdateBody =
  paths["/api/lists/{list_id}/entries/{entry_id}"]["patch"]["requestBody"]["content"]["application/json"]

export async function listLists(
  params: { kind?: ListKind; limit?: number; offset?: number },
  accessToken: string | null,
): Promise<ListListResponse> {
  const q = new URLSearchParams()
  if (params.kind) q.set("kind", params.kind)
  if (params.limit !== undefined) q.set("limit", String(params.limit))
  if (params.offset !== undefined) q.set("offset", String(params.offset))
  const res = await apiFetch(`/lists${q.size ? `?${q}` : ""}`, { accessToken })
  return (await res.json()) as ListListResponse
}

export async function createList(
  body: ListCreateBody,
  accessToken: string | null,
): Promise<ListSummary> {
  const res = await apiFetch("/lists", {
    method: "POST",
    accessToken,
    body: JSON.stringify(body),
  })
  return (await res.json()) as ListSummary
}

export async function getList(id: string, accessToken: string | null): Promise<ListDetail> {
  const res = await apiFetch(`/lists/${id}`, { accessToken })
  return (await res.json()) as ListDetail
}

export async function updateList(
  id: string,
  body: ListUpdateBody,
  accessToken: string | null,
): Promise<ListSummary> {
  const res = await apiFetch(`/lists/${id}`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(body),
  })
  return (await res.json()) as ListSummary
}

export async function deleteList(id: string, accessToken: string | null): Promise<void> {
  await apiFetch(`/lists/${id}`, { method: "DELETE", accessToken })
}

export async function createEntry(
  listId: string,
  body: EntryCreateBody,
  accessToken: string | null,
): Promise<ListEntry> {
  const res = await apiFetch(`/lists/${listId}/entries`, {
    method: "POST",
    accessToken,
    body: JSON.stringify(body),
  })
  return (await res.json()) as ListEntry
}

export async function updateEntry(
  listId: string,
  entryId: string,
  body: EntryUpdateBody,
  accessToken: string | null,
): Promise<ListEntry> {
  const res = await apiFetch(`/lists/${listId}/entries/${entryId}`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(body),
  })
  return (await res.json()) as ListEntry
}

export async function toggleEntry(
  listId: string,
  entryId: string,
  accessToken: string | null,
): Promise<ListEntry> {
  const res = await apiFetch(`/lists/${listId}/entries/${entryId}/toggle`, {
    method: "POST",
    accessToken,
  })
  return (await res.json()) as ListEntry
}

export async function deleteEntry(
  listId: string,
  entryId: string,
  accessToken: string | null,
): Promise<void> {
  await apiFetch(`/lists/${listId}/entries/${entryId}`, {
    method: "DELETE",
    accessToken,
  })
}

export async function reorderEntries(
  listId: string,
  entryIds: string[],
  accessToken: string | null,
): Promise<void> {
  await apiFetch(`/lists/${listId}/entries/reorder`, {
    method: "POST",
    accessToken,
    body: JSON.stringify({ entry_ids: entryIds }),
  })
}
