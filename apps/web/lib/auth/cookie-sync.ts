"use client"

import { useEffect } from "react"

import { useAuthStore } from "./auth-store"

const COOKIE_NAME = "ims_token"
const MAX_AGE_SECONDS = 60 * 60 * 24 * 7 // 7 days

export function writeTokenCookie(hasToken: boolean): void {
  if (typeof document === "undefined") return
  document.cookie = hasToken
    ? `${COOKIE_NAME}=1; Path=/; SameSite=Lax; Max-Age=${MAX_AGE_SECONDS}`
    : `${COOKIE_NAME}=; Path=/; SameSite=Lax; Max-Age=0`
}

/**
 * 於 mount 當下同步一次目前 token 狀態到 cookie，並訂閱後續變化。
 * 回傳值為 unsubscribe function（由 useEffect cleanup 呼叫）。
 */
export function useTokenCookieSync(): void {
  useEffect(() => {
    writeTokenCookie(Boolean(useAuthStore.getState().accessToken))
    return useAuthStore.subscribe((state, prev) => {
      if (state.accessToken !== prev.accessToken) {
        writeTokenCookie(Boolean(state.accessToken))
      }
    })
  }, [])
}
