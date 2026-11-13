"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/profile"
import { STALE_TIME } from "./constants"
import { useAuthStore } from "@/lib/auth/auth-store"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useMe() {
  const token = useAccessToken()
  return useQuery({ queryKey: ["profile", "me"], queryFn: () => api.getMe(token), enabled: token !== null, staleTime: STALE_TIME })
}

export function useUpdateProfile() {
  const token = useAccessToken()
  const qc = useQueryClient()
  const setAuth = useAuthStore((s) => s.setAuth)
  return useMutation({
    mutationFn: (body: api.UserProfileUpdate) => api.updateProfile(body, token),
    onSuccess: (user) => {
      const currentToken = useAuthStore.getState().accessToken ?? ""
      setAuth(currentToken, user)
      qc.invalidateQueries({ queryKey: ["profile"] })
    },
  })
}

export function useChangePassword() {
  const token = useAccessToken()
  const setAccessToken = useAuthStore((s) => s.setAccessToken)
  return useMutation({
    mutationFn: (body: api.PasswordChangeBody) => api.changePassword(body, token),
    // 改密碼會讓所有舊 token 失效：必須把新 access token 寫回 store，否則下一個請求就 401
    onSuccess: (result) => setAccessToken(result.access_token),
  })
}

export function useBootstrapAdmin() {
  const token = useAccessToken()
  const qc = useQueryClient()
  const setAuth = useAuthStore((s) => s.setAuth)
  return useMutation({
    mutationFn: () => api.bootstrapAdmin(token),
    onSuccess: (user) => {
      const currentToken = useAuthStore.getState().accessToken ?? ""
      setAuth(currentToken, user)
      qc.invalidateQueries({ queryKey: ["profile"] })
    },
  })
}
