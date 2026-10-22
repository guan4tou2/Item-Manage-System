"use client"

import { keepPreviousData, useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/audit"
import { useAccessToken } from "@/lib/auth/use-auth"

/** 每頁筆數（與 API 預設值一致）。 */
export const AUDIT_PAGE_SIZE = 50

export function useAuditLogs(
  filters: api.AuditFilters,
  page: { limit: number; offset: number },
) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["admin", "audit-logs", filters, page],
    queryFn: () => api.listAuditLogs(filters, page, token),
    // 翻頁／改篩選時保留上一頁資料，避免表格閃白
    placeholderData: keepPreviousData,
    enabled: token !== null,
    staleTime: 30_000,
  })
}
