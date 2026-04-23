"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/admin"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useAdminUsers(enabled: boolean) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api.listUsers(token),
    enabled: enabled && token !== null,
    staleTime: 30_000,
  })
}

export function useSetUserActive() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      api.setUserActive(userId, isActive, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }),
  })
}

export function useSendTestNotification() {
  const token = useAccessToken()
  return useMutation({
    mutationFn: (userId: string) => api.sendTestNotification(userId, token),
  })
}
