"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api/client"
import { useAccessToken } from "@/lib/auth/use-auth"

import type { PreferencesRead, PreferencesUpdate } from "./types"

const KEY = ["preferences", "me"] as const

export function usePreferences() {
  const accessToken = useAccessToken()
  return useQuery<PreferencesRead>({
    queryKey: KEY,
    queryFn: async () => {
      const res = await apiFetch("/users/me/preferences", { accessToken })
      return (await res.json()) as PreferencesRead
    },
    enabled: Boolean(accessToken),
    staleTime: 5 * 60_000,
  })
}

export function useUpdatePreferences() {
  const accessToken = useAccessToken()
  const qc = useQueryClient()
  return useMutation<PreferencesRead, Error, PreferencesUpdate>({
    mutationFn: async (body) => {
      const res = await apiFetch("/users/me/preferences", {
        method: "PUT",
        body: JSON.stringify(body),
        accessToken,
      })
      return (await res.json()) as PreferencesRead
    },
    onSuccess: (data) => {
      qc.setQueryData(KEY, data)
    },
  })
}
