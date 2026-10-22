import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type AuditLogPage =
  paths["/api/admin/audit-logs"]["get"]["responses"]["200"]["content"]["application/json"]

export type AuditLogRead = AuditLogPage["items"][number]

export type AuditFacetValue = AuditLogPage["facets"]["actions"][number]

/** 稽核查詢條件（空字串視同未提供）。 */
export interface AuditFilters {
  action?: string
  resource_type?: string
  user_id?: string
  q?: string
  created_from?: string
  created_to?: string
}

const FILTER_KEYS = [
  "action",
  "resource_type",
  "user_id",
  "q",
  "created_from",
  "created_to",
] as const

/** 組查詢字串（順序固定，方便測試與快取鍵穩定）。 */
export function auditQueryString(
  filters: AuditFilters = {},
  page: { limit?: number; offset?: number } = {},
): string {
  const params = new URLSearchParams()
  if (page.limit !== undefined) params.set("limit", String(page.limit))
  if (page.offset !== undefined) params.set("offset", String(page.offset))
  for (const key of FILTER_KEYS) {
    const value = filters[key]
    if (value !== undefined && value !== "") params.set(key, value)
  }
  const query = params.toString()
  return query === "" ? "" : `?${query}`
}

export async function listAuditLogs(
  filters: AuditFilters,
  page: { limit: number; offset: number },
  accessToken: string | null,
): Promise<AuditLogPage> {
  const res = await apiFetch(
    `/admin/audit-logs${auditQueryString(filters, page)}`,
    { accessToken },
  )
  return (await res.json()) as AuditLogPage
}

export async function exportAuditLogs(
  filters: AuditFilters,
  accessToken: string | null,
): Promise<{ blob: Blob; filename: string }> {
  const res = await apiFetch(
    `/admin/audit-logs/export.csv${auditQueryString(filters)}`,
    { accessToken },
  )
  const disposition = res.headers.get("content-disposition") ?? ""
  const match = /filename="([^"]+)"/.exec(disposition)
  return {
    blob: await res.blob(),
    filename: match?.[1] ?? "audit-logs.csv",
  }
}
