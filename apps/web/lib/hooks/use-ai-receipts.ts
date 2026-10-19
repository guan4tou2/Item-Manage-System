"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/ai-receipts"
import { useAccessToken } from "@/lib/auth/use-auth"

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
