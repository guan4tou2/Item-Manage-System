"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/ai-receipts"
import type { DraftListResponse } from "@/lib/api/ai-drafts"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useAccessToken } from "@/lib/auth/use-auth"

import { STALE_TIME } from "./constants"

/** 收據草稿與一般草稿共用佇列快取前綴。 */
const DRAFTS_KEY = ["ai-drafts"] as const

/**
 * 多頁收據 → 品項草稿（Phase 33）。
 *
 * 成功後草稿即為 `ready`（建立時抽取完成），只需讓佇列與計數失效重取。
 */
export function useCreateReceipt() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (imageIds: string[]) => api.createReceipt(imageIds, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DRAFTS_KEY })
    },
  })
}

export const RECEIPTS_KEY = ["ai-receipts"] as const

export function useReceipt(id: string) {
  const token = useAccessToken()
  const readOnly = useReadOnly()
  return useQuery({
    queryKey: [...RECEIPTS_KEY, id],
    queryFn: () => api.getReceipt(id, token),
    enabled: token !== null && !readOnly,
    staleTime: STALE_TIME,
    retry: false,
  })
}

/** 只更新同一收據的欄位，保留快取中其他草稿的最新狀態。 */
export function useReceiptReview(id: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  const key = [...RECEIPTS_KEY, id]
  const update = (review: api.ReceiptReview | null) => {
    qc.setQueriesData<DraftListResponse>({ queryKey: [...DRAFTS_KEY, "list"] }, (old) =>
      old ? { ...old, items: old.items.map((draft) =>
        draft.receipt_id === id ? { ...draft, receipt_review: review } : draft,
      ) } : old,
    )
    qc.setQueryData<api.ReceiptRead>(key, (old) => old ? { ...old, review } : old)
  }
  return useMutation({
    mutationKey: [...key, "review"],
    scope: { id: `receipt-review-${id}` },
    mutationFn: async (note: string | null | undefined) => {
      if (note === undefined) {
        await api.deleteReceiptReview(id, token)
        return null
      }
      return api.putReceiptReview(id, note, token)
    },
    onMutate: async (note) => {
      await Promise.all([
        qc.cancelQueries({ queryKey: DRAFTS_KEY }),
        qc.cancelQueries({ queryKey: key }),
      ])
      const lists = qc.getQueriesData<DraftListResponse>({ queryKey: [...DRAFTS_KEY, "list"] })
      const detail = qc.getQueryData<api.ReceiptRead>(key)
      const previous = detail?.review ?? lists.flatMap(([, data]) => data?.items ?? [])
        .find((draft) => draft.receipt_id === id)?.receipt_review ?? null
      update(note === undefined ? null : {
        verified_at: previous?.verified_at ?? new Date().toISOString(), note,
      })
      return { lists, detail }
    },
    onError: (_error, _note, context) => {
      // 回滾核對欄位，避免覆蓋同時接受／捨棄草稿造成的其他變化。
      for (const [listKey, previous] of context?.lists ?? []) {
        qc.setQueryData<DraftListResponse>(listKey, (current) => current ? {
          ...current, items: current.items.map((draft) => draft.receipt_id === id ? {
            ...draft, receipt_review: previous?.items.find((row) => row.id === draft.id)?.receipt_review ?? null,
          } : draft),
        } : current)
      }
      qc.setQueryData<api.ReceiptRead>(key, (current) => current ? {
        ...current, review: context?.detail?.review ?? null,
      } : current)
    },
    onSuccess: (review) => update(review),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: DRAFTS_KEY })
      qc.invalidateQueries({ queryKey: key })
    },
  })
}
