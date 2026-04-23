"use client"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toggleFavorite } from "@/lib/api/favorites"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useToggleFavorite() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => toggleFavorite(itemId, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  })
}
