"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/ai-drafts"
import type { DraftAcceptRequest, DraftCounts, DraftStatus } from "@/lib/api/ai-drafts"
import { useAccessToken } from "@/lib/auth/use-auth"

import { STALE_TIME } from "./constants"

/** 草稿相關快取前綴（佇列清單與計數共用）。 */
const DRAFTS_KEY = ["ai-drafts"] as const

export function useDrafts(
  params: { status?: DraftStatus; limit?: number; offset?: number } = {},
) {
  const token = useAccessToken()
  const { status, limit = 20, offset = 0 } = params
  return useQuery({
    queryKey: [...DRAFTS_KEY, "list", { status: status ?? null, limit, offset }],
    queryFn: () => api.listDrafts({ status, limit, offset }, token),
    enabled: token !== null,
    staleTime: STALE_TIME,
  })
}

/** 六態計數（入口卡徽章／分頁頁籤）；僅取 1 列清單以降低負載。 */
export function useDraftCounts() {
  const token = useAccessToken()
  return useQuery({
    queryKey: [...DRAFTS_KEY, "counts"],
    queryFn: async (): Promise<DraftCounts> => {
      const res = await api.listDrafts({ limit: 1, offset: 0 }, token)
      return res.counts
    },
    enabled: token !== null,
    staleTime: STALE_TIME,
  })
}

function invalidateDrafts(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: DRAFTS_KEY })
  qc.invalidateQueries({ queryKey: ["ai-receipts"] })
}

export function useCreateDrafts() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (imageIds: string[]) => api.createDrafts(imageIds, token),
    onSuccess: () => invalidateDrafts(qc),
  })
}

export function useProcessDraft() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.processDraft(id, token),
    onSuccess: () => invalidateDrafts(qc),
  })
}

export function useAcceptDraft() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: DraftAcceptRequest }) =>
      api.acceptDraft(id, body, token),
    onSuccess: () => {
      invalidateDrafts(qc)
      // 接受即建立物品 → 清單／詳情／統計一併失效
      qc.invalidateQueries({ queryKey: ["items"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
    },
  })
}

export function useDiscardDraft() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.discardDraft(id, token),
    onSuccess: () => invalidateDrafts(qc),
  })
}

export function useDiscardDrafts() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => api.discardDrafts(ids, token),
    onSuccess: () => invalidateDrafts(qc),
  })
}

export function useSuggestClassification() {
  const token = useAccessToken()
  return useMutation({
    mutationFn: (name: string) => api.suggestClassification(name, token),
  })
}
