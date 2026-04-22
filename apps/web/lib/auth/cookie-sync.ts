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
 * 同步目前 token 狀態到 cookie，並訂閱後續變化。
 *
 * 必須等 Zustand persist 完成 localStorage 重建後才寫 cookie，
 * 否則 cold load 會誤把還沒 rehydrate 的 null token 當成登出狀態，
 * 把 cookie 清掉並害 middleware 把使用者踢回 /login。
 */
export function useTokenCookieSync(): void {
  useEffect(() => {
    function syncNow(): void {
      writeTokenCookie(Boolean(useAuthStore.getState().accessToken))
    }

    // 若已經 rehydrate（熱路徑／後續 mount），立即寫一次
    if (useAuthStore.persist.hasHydrated()) {
      syncNow()
    }

    const unsubHydration = useAuthStore.persist.onFinishHydration(syncNow)
    const unsubStore = useAuthStore.subscribe((state, prev) => {
      if (state.accessToken !== prev.accessToken) {
        writeTokenCookie(Boolean(state.accessToken))
      }
    })
    return () => {
      unsubHydration()
      unsubStore()
    }
  }, [])
}
