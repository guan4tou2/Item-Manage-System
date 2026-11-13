import type { paths } from '@ims/api-types'
import { useAuthStore } from '@/lib/auth/auth-store'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api'

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`api error ${status}`)
  }
}

type RequestInitWithToken = RequestInit & { accessToken?: string | null }

// 進行中的 refresh（single-flight）：多個請求同時 401 時共用，避免後端 cookie 被重複輪替
let refreshInFlight: Promise<string | null> | null = null

/** 以 httpOnly refresh cookie 換新 access token；成功寫回 store 並回傳新 token，失敗回 null。 */
function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'include' })
        if (!res.ok) return null
        const data = (await res.json().catch(() => null)) as { access_token?: unknown } | null
        if (typeof data?.access_token !== 'string' || !data.access_token) return null
        useAuthStore.getState().setAccessToken(data.access_token)
        return data.access_token
      } catch {
        return null
      } finally {
        refreshInFlight = null
      }
    })()
  }
  return refreshInFlight
}

function sendRequest(path: string, init: RequestInitWithToken, token: string | null | undefined): Promise<Response> {
  const { accessToken: _ignored, ...rest } = init
  const headers = new Headers(init.headers)
  // Only set JSON content-type when body is not FormData (browser sets boundary for FormData)
  if (!(init.body instanceof FormData) && !headers.has('content-type')) {
    headers.set('content-type', 'application/json')
  }
  if (token) {
    headers.set('authorization', `Bearer ${token}`)
  }
  return fetch(`${API_BASE}${path}`, { ...rest, headers, credentials: 'include' })
}

export async function apiFetch(path: string, init: RequestInitWithToken = {}): Promise<Response> {
  let response = await sendRequest(path, init, init.accessToken)
  if (response.status === 401 && init.accessToken && !path.startsWith('/auth/')) {
    // access token 過期：若 store 的 token 已被別的請求更新就直接沿用，否則 single-flight refresh
    const current = useAuthStore.getState().accessToken
    // store 已被清空（例如使用者剛登出）時不嘗試 refresh，避免復活已結束的 session
    const newToken = current === null ? null : current !== init.accessToken ? current : await refreshAccessToken()
    if (newToken) {
      // 只重試一次；重試後仍 401 則落入下方清 store 流程，不再循環
      response = await sendRequest(path, init, newToken)
    }
  }
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

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError
}

export function getApiErrorDetail(err: unknown): string | undefined {
  if (!isApiError(err)) return undefined
  const body = err.body as Record<string, unknown> | null
  return typeof body?.detail === "string" ? body.detail : undefined
}

/** 取得 FastAPI 422 驗證錯誤陣列中的所有 msg（`detail` 為字串時回傳單元素陣列）。 */
export function getApiErrorMessages(err: unknown): string[] {
  if (!isApiError(err)) return []
  const detail = (err.body as Record<string, unknown> | null)?.detail
  if (typeof detail === 'string') return [detail]
  if (!Array.isArray(detail)) return []
  return detail.flatMap((d) => {
    const msg = (d as { msg?: unknown } | null)?.msg
    return typeof msg === 'string' ? [msg] : []
  })
}

export type Paths = paths
