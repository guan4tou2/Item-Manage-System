"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/profile"
import { useAuthStore } from "@/lib/auth/auth-store"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useMe() {
  const token = useAccessToken()
  return useQuery({ queryKey: ["profile", "me"], queryFn: () => api.getMe(token), enabled: token !== null, staleTime: 30_000 })
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
  return useMutation({
    mutationFn: (body: api.PasswordChangeBody) => api.changePassword(body, token),
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
