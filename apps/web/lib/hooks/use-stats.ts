"use client"

import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/stats"
import { useAccessToken } from "@/lib/auth/use-auth"

const STALE = 30_000

export function useOverview() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "overview"],
    queryFn: () => api.getOverview(token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useByCategory() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "by-category"],
    queryFn: () => api.getByCategory(token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useByLocation() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "by-location"],
    queryFn: () => api.getByLocation(token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useByTag(limit = 10) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "by-tag", limit],
    queryFn: () => api.getByTag(limit, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useByWarehouse() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "by-warehouse"],
    queryFn: () => api.getByWarehouse(token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useRecent(limit = 5) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "recent", limit],
    queryFn: () => api.getRecent(limit, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useLowStock(limit = 10) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "low-stock", limit],
    queryFn: () => api.getLowStock(limit, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useActiveLoans(limit = 10) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "active-loans", limit],
    queryFn: () => api.getActiveLoans(limit, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useTrend(days = 30) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "trend", days],
    queryFn: () => api.getTrend(days, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useActivity(limit = 20) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "activity", limit],
    queryFn: () => api.getActivity(limit, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}
