"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/notifications"
import { useAccessToken } from "@/lib/auth/use-auth"

const STALE = 30_000

export function useNotifications(params: { unreadOnly?: boolean; limit?: number; offset?: number } = {}) {
  const token = useAccessToken()
  const { unreadOnly = false, limit = 20, offset = 0 } = params
  return useQuery({
    queryKey: ["notifications", "list", { unreadOnly, limit, offset }],
    queryFn: () => api.listNotifications({ unreadOnly, limit, offset }, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useUnreadCount() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api.getUnreadCount(token),
    enabled: token !== null,
    staleTime: STALE,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}

export function useMarkNotificationRead() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.markNotificationRead(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] })
    },
  })
}

export function useMarkAllNotificationsRead() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.markAllNotificationsRead(token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] })
    },
  })
}

export function useDeleteNotification() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteNotification(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] })
    },
  })
}
