import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type ReportRead =
  paths["/api/reports"]["get"]["responses"]["200"]["content"]["application/json"]["items"][number]

export type ReportListResponse =
  paths["/api/reports"]["get"]["responses"]["200"]["content"]["application/json"]

export type ReportPayload = ReportRead["payload"]

export type ReportBucket = ReportPayload["top_categories"][number]

export async function listReports(
  params: { limit?: number; offset?: number },
  accessToken: string | null,
): Promise<ReportListResponse> {
  const q = new URLSearchParams()
  if (params.limit !== undefined) q.set("limit", String(params.limit))
  if (params.offset !== undefined) q.set("offset", String(params.offset))
  const suffix = q.size > 0 ? `?${q.toString()}` : ""
  const res = await apiFetch(`/reports${suffix}`, { accessToken })
  return (await res.json()) as ReportListResponse
}

export async function getReport(
  id: string,
  accessToken: string | null,
): Promise<ReportRead> {
  const res = await apiFetch(`/reports/${id}`, { accessToken })
  return (await res.json()) as ReportRead
}
