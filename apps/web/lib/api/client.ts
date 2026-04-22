import type { paths } from '@ims/api-types'
import { useAuthStore } from '@/lib/auth/auth-store'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api'

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`api error ${status}`)
  }
}

type RequestInitWithToken = RequestInit & { accessToken?: string | null }

export async function apiFetch(path: string, init: RequestInitWithToken = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set('content-type', 'application/json')
  if (init.accessToken) {
    headers.set('authorization', `Bearer ${init.accessToken}`)
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (response.status === 401) {
      // Token is actually invalid → clear store (cookie-sync subscriber will clear the cookie)
      useAuthStore.getState().clear()
    }
    throw new ApiError(response.status, body)
  }
  return response
}

export type Paths = paths
