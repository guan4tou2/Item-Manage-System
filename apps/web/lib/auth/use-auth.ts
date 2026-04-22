'use client'

import { useMutation } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api/client'
import { useAuthStore } from './auth-store'
import type { paths } from '@ims/api-types'

type LoginBody = paths['/api/auth/login']['post']['requestBody']['content']['application/json']
type TokenResponse = paths['/api/auth/login']['post']['responses']['200']['content']['application/json']

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)
  return useMutation({
    mutationFn: async (body: LoginBody) => {
      const res = await apiFetch('/auth/login', { method: 'POST', body: JSON.stringify(body) })
      return (await res.json()) as TokenResponse
    },
    onSuccess: (data) => {
      setAuth(data.access_token, data.user)
    },
  })
}

export function useLogout() {
  const clear = useAuthStore((s) => s.clear)
  return useMutation({
    mutationFn: async () => {
      await apiFetch('/auth/logout', { method: 'POST' })
    },
    onSuccess: () => clear(),
  })
}

export function useCurrentUser() {
  return useAuthStore((s) => s.user)
}

export function useAccessToken() {
  return useAuthStore((s) => s.accessToken)
}
