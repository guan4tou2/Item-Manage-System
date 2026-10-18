"use client"

import { useAuthStore } from "./auth-store"

/**
 * Phase 30：是否為唯讀檢視者（viewer）。
 *
 * 來源為 `UserPublic.is_read_only`（login／register／`/users/me`）。
 * `MeSync` 於 app 啟動時以 `/users/me` 同步，讓 session 中的角色變更即時生效。
 */
export function useReadOnly(): boolean {
  return useAuthStore((s) => s.user?.is_read_only ?? false)
}
