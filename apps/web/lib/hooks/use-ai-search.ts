"use client"

import { useMutation } from "@tanstack/react-query"

import * as api from "@/lib/api/ai-search"
import { useAccessToken } from "@/lib/auth/use-auth"

/**
 * AI 自然語言搜尋（Phase 34）。
 *
 * 搜尋結果不進快取（每次句子不同、且含 AI 理解結果），以 mutation 呈現
 * 「送出 → 理解中 → 結果」的單次流程。
 */
export function useAiSearch() {
  const token = useAccessToken()
  return useMutation({
    mutationFn: (query: string) => api.aiSearch(query, token),
  })
}

/** 物品問答：每次提問獨立（單輪），以 mutation 呈現。 */
export function useAiAsk() {
  const token = useAccessToken()
  return useMutation({
    mutationFn: ({ question, itemIds }: { question: string; itemIds: string[] }) =>
      api.askItems(question, itemIds, token),
  })
}
