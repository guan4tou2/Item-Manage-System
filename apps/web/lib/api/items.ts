import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type ItemRead = paths["/api/items/{item_id}"]["get"]["responses"]["200"]["content"]["application/json"]
type ItemListResponse = paths["/api/items"]["get"]["responses"]["200"]["content"]["application/json"]
type ItemCreate = paths["/api/items"]["post"]["requestBody"]["content"]["application/json"]
type ItemUpdate = paths["/api/items/{item_id}"]["patch"]["requestBody"]["content"]["application/json"]
type ItemBulkUpdate = paths["/api/items/bulk"]["patch"]["requestBody"]["content"]["application/json"]
type ItemBulkDelete = paths["/api/items/bulk-delete"]["post"]["requestBody"]["content"]["application/json"]
type ItemBulkResult = paths["/api/items/bulk"]["patch"]["responses"]["200"]["content"]["application/json"]

export type {
  ItemRead,
  ItemListResponse,
  ItemCreate,
  ItemUpdate,
  ItemBulkUpdate,
  ItemBulkDelete,
  ItemBulkResult,
}

export interface ItemFilters {
  q?: string
  categoryId?: number
  locationId?: number
  /** 位置篩選範圍：預設 `subtree`（含子孫）；`exact`＝僅此層（「僅此層」toggle）。 */
  locationScope?: "subtree" | "exact"
  tagIds?: number[]
  expiry?: "expired" | "expiring_soon"
  /** Phase 34：借出狀態（`borrowed` 未歸還／`overdue` 逾期未還）。 */
  loan?: "borrowed" | "overdue"
  /** Phase 34：數量區間（含邊界）。 */
  minQuantity?: number
  maxQuantity?: number
  sort?: "expiry_asc" | "name_asc" | "created_desc"
  page?: number
  perPage?: number
}

function buildQuery(filters: ItemFilters): string {
  const params = new URLSearchParams()
  if (filters.q) params.set("q", filters.q)
  if (filters.categoryId != null) params.set("category_id", String(filters.categoryId))
  if (filters.locationId != null) params.set("location_id", String(filters.locationId))
  if (filters.locationId != null && filters.locationScope === "exact") {
    params.set("location_scope", "exact")
  }
  if (filters.tagIds && filters.tagIds.length > 0) {
    for (const id of filters.tagIds) params.append("tag_ids", String(id))
  }
  if (filters.expiry) params.set("expiry", filters.expiry)
  if (filters.loan) params.set("loan", filters.loan)
  if (filters.minQuantity != null) params.set("min_quantity", String(filters.minQuantity))
  if (filters.maxQuantity != null) params.set("max_quantity", String(filters.maxQuantity))
  if (filters.sort) params.set("sort", filters.sort)
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

export async function createItem(body: ItemCreate, accessToken: string | null, idempotencyKey?: string): Promise<ItemRead> {
  const res = await apiFetch("/items", {
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
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

export async function bulkUpdateItems(
  body: ItemBulkUpdate,
  accessToken: string | null,
): Promise<ItemBulkResult> {
  const res = await apiFetch("/items/bulk", {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as ItemBulkResult
}

export async function bulkDeleteItems(
  body: ItemBulkDelete,
  accessToken: string | null,
): Promise<ItemBulkResult> {
  const res = await apiFetch("/items/bulk-delete", {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as ItemBulkResult
}

export async function deleteItem(id: string, accessToken: string | null): Promise<void> {
  await apiFetch(`/items/${id}`, { method: "DELETE", accessToken })
}
