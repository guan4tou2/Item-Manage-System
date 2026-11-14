"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/list-shares"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useListShares(listId: string) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["list-shares", listId],
    queryFn: () => api.listShares(listId, token),
    enabled: token !== null,
    staleTime: 0,
  })
}

export function useCreateListShare(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: api.ShareCreateBody) => api.createShare(listId, body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["list-shares", listId] }),
    // 完整 token 由對話框短暫持有，關閉後立即回收 mutation cache。
    gcTime: 0,
  })
}

export function useRevokeListShare(listId: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (shareId: string) => api.revokeShare(listId, shareId, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["list-shares", listId] }),
  })
}
