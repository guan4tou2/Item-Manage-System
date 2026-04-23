import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type OverviewStats = paths["/api/stats/overview"]["get"]["responses"]["200"]["content"]["application/json"]
export type CategoryBucket = paths["/api/stats/by-category"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type LocationBucket = paths["/api/stats/by-location"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type TagBucket = paths["/api/stats/by-tag"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type WarehouseBucket = paths["/api/stats/by-warehouse"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type RecentItem = paths["/api/stats/recent"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type LowStockItem = paths["/api/stats/low-stock"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type ActiveLoan = paths["/api/stats/active-loans"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type TrendPoint = paths["/api/stats/trend"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type ActivityEntry = paths["/api/stats/activity"]["get"]["responses"]["200"]["content"]["application/json"][number]

export async function getOverview(accessToken: string | null): Promise<OverviewStats> {
  const res = await apiFetch("/stats/overview", { accessToken })
  return (await res.json()) as OverviewStats
}

export async function getByCategory(accessToken: string | null): Promise<CategoryBucket[]> {
  const res = await apiFetch("/stats/by-category", { accessToken })
  return (await res.json()) as CategoryBucket[]
}

export async function getByLocation(accessToken: string | null): Promise<LocationBucket[]> {
  const res = await apiFetch("/stats/by-location", { accessToken })
  return (await res.json()) as LocationBucket[]
}

export async function getByTag(limit: number, accessToken: string | null): Promise<TagBucket[]> {
  const res = await apiFetch(`/stats/by-tag?limit=${limit}`, { accessToken })
  return (await res.json()) as TagBucket[]
}

export async function getByWarehouse(accessToken: string | null): Promise<WarehouseBucket[]> {
  const res = await apiFetch("/stats/by-warehouse", { accessToken })
  return (await res.json()) as WarehouseBucket[]
}

export async function getRecent(limit: number, accessToken: string | null): Promise<RecentItem[]> {
  const res = await apiFetch(`/stats/recent?limit=${limit}`, { accessToken })
  return (await res.json()) as RecentItem[]
}

export async function getLowStock(limit: number, accessToken: string | null): Promise<LowStockItem[]> {
  const res = await apiFetch(`/stats/low-stock?limit=${limit}`, { accessToken })
  return (await res.json()) as LowStockItem[]
}

export async function getActiveLoans(limit: number, accessToken: string | null): Promise<ActiveLoan[]> {
  const res = await apiFetch(`/stats/active-loans?limit=${limit}`, { accessToken })
  return (await res.json()) as ActiveLoan[]
}

export async function getTrend(days: number, accessToken: string | null): Promise<TrendPoint[]> {
  const res = await apiFetch(`/stats/trend?days=${days}`, { accessToken })
  return (await res.json()) as TrendPoint[]
}

export async function getActivity(limit: number, accessToken: string | null): Promise<ActivityEntry[]> {
  const res = await apiFetch(`/stats/activity?limit=${limit}`, { accessToken })
  return (await res.json()) as ActivityEntry[]
}
