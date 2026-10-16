"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { getApiErrorDetail } from "@/lib/api/client"
import * as api from "@/lib/api/notification-preferences"
import { useAccessToken } from "@/lib/auth/use-auth"

import { STALE_TIME } from "./constants"

export const notificationPreferencesQueryKey = ["notification-preferences"] as const

export function useNotificationPreferences() {
  const token = useAccessToken()
  return useQuery({
    queryKey: notificationPreferencesQueryKey,
    queryFn: () => api.getNotificationPreferences(token),
    enabled: token !== null,
    staleTime: STALE_TIME,
  })
}

export function useUpdateNotificationPreferences() {
  const token = useAccessToken()
  const qc = useQueryClient()
  const t = useTranslations("settings.notificationPreferences")
  return useMutation({
    mutationFn: (updates: api.NotificationPreferenceUpdate[]) =>
      api.updateNotificationPreferences(updates, token),
    onMutate: async (updates) => {
      await qc.cancelQueries({ queryKey: notificationPreferencesQueryKey })
      const previous =
        qc.getQueryData<api.NotificationPreferencesResponse>(
          notificationPreferencesQueryKey,
        )
      if (previous) {
        const matrix = { ...previous.matrix }
        for (const update of updates) {
          matrix[update.type] = { ...matrix[update.type], [update.channel]: update.enabled }
        }
        // has_custom 的伺服器正解需知預設值；樂觀期間一律視為有覆寫，
        // onSuccess 會以伺服器 snapshot 覆蓋。
        qc.setQueryData(notificationPreferencesQueryKey, {
          ...previous,
          matrix,
          has_custom: true,
        })
      }
      return { previous }
    },
    onError: (error, _updates, context) => {
      if (context?.previous) {
        qc.setQueryData(notificationPreferencesQueryKey, context.previous)
      }
      toast.error(getApiErrorDetail(error) ?? t("toast.updateFailed"))
    },
    onSuccess: (snapshot) => {
      qc.setQueryData(notificationPreferencesQueryKey, snapshot)
      toast.success(t("toast.updated"))
    },
  })
}

export function useResetNotificationPreferences() {
  const token = useAccessToken()
  const qc = useQueryClient()
  const t = useTranslations("settings.notificationPreferences")
  return useMutation({
    mutationFn: () => api.resetNotificationPreferences(token),
    onSuccess: (snapshot) => {
      qc.setQueryData(notificationPreferencesQueryKey, snapshot)
      toast.success(t("toast.reset"))
    },
    onError: (error) => {
      toast.error(getApiErrorDetail(error) ?? t("toast.resetFailed"))
    },
  })
}
