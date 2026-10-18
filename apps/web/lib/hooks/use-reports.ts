"use client"

import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/reports"
import { useAccessToken } from "@/lib/auth/use-auth"

import { STALE_TIME } from "./constants"

export function useReports(params: { limit?: number; offset?: number } = {}) {
  const token = useAccessToken()
  const { limit = 20, offset = 0 } = params
  return useQuery({
    queryKey: ["reports", "list", { limit, offset }],
    queryFn: () => api.listReports({ limit, offset }, token),
    enabled: token !== null,
    staleTime: STALE_TIME,
  })
}

export function useReport(id: string) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["reports", "detail", id],
    queryFn: () => api.getReport(id, token),
    enabled: token !== null && id !== "",
    staleTime: STALE_TIME,
  })
}
