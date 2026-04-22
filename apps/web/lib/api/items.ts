import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type ItemRead = paths["/api/items/{item_id}"]["get"]["responses"]["200"]["content"]["application/json"]
type ItemListResponse = paths["/api/items"]["get"]["responses"]["200"]["content"]["application/json"]
type ItemCreate = paths["/api/items"]["post"]["requestBody"]["content"]["application/json"]
type ItemUpdate = paths["/api/items/{item_id}"]["patch"]["requestBody"]["content"]["application/json"]

export type { ItemRead, ItemListResponse, ItemCreate, ItemUpdate }

export interface ItemFilters {
  q?: string
  categoryId?: number
  locationId?: number
  tagIds?: number[]
  page?: number
  perPage?: number
}

function buildQuery(filters: ItemFilters): string {
  const params = new URLSearchParams()
  if (filters.q) params.set("q", filters.q)
  if (filters.categoryId != null) params.set("category_id", String(filters.categoryId))
  if (filters.locationId != null) params.set("location_id", String(filters.locationId))
  if (filters.tagIds && filters.tagIds.length > 0) {
    for (const id of filters.tagIds) params.append("tag_ids", String(id))
  }
  if (filters.page != null) params.set("page", String(filters.page))
  if (filters.perPage != null) params.set("per_page", String(filters.perPage))
  const s = params.toString()
  return s ? `?${s}` : ""
}

export async function listItems(filters: ItemFilters, accessToken: string | null): Promise<ItemListResponse> {
  const res = await apiFetch(`/items${buildQuery(filters)}`, { accessToken })
  return (await res.json()) as ItemListResponse
}

export async function getItem(id: string, accessToken: string | null): Promise<ItemRead> {
  const res = await apiFetch(`/items/${id}`, { accessToken })
  return (await res.json()) as ItemRead
}

export async function createItem(body: ItemCreate, accessToken: string | null): Promise<ItemRead> {
  const res = await apiFetch("/items", {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as ItemRead
}

export async function updateItem(id: string, body: ItemUpdate, accessToken: string | null): Promise<ItemRead> {
  const res = await apiFetch(`/items/${id}`, {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as ItemRead
}

export async function deleteItem(id: string, accessToken: string | null): Promise<void> {
  await apiFetch(`/items/${id}`, { method: "DELETE", accessToken })
}
