"use client"

import { useEffect } from "react"

import { useAuthStore } from "@/lib/auth/auth-store"
import { useMe } from "@/lib/hooks/use-profile"

/**
 * Phase 30：以 `/users/me` 同步 auth store。
 *
 * login／register 已帶 `is_read_only`；此同步讓**session 中被變更角色**
 * （升／降為 viewer）的使用者在下一次載入即取得最新狀態。
 */
export function MeSync() {
  const token = useAuthStore((s) => s.accessToken)
  const setAuth = useAuthStore((s) => s.setAuth)
  const me = useMe()

  useEffect(() => {
    if (token && me.data) {
      setAuth(token, me.data)
    }
  }, [token, me.data, setAuth])

  return null
}
