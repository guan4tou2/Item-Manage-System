"use client"

import { useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { useEffect } from "react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/lib/auth/auth-store"
import { currentSession, offlineQueue, refreshOffline, useOnline, usePendingItems, useOfflineState } from "@/lib/offline/runtime"

export function useOfflineSync() {
  const t = useTranslations("offline")
  const qc = useQueryClient()
  const router = useRouter()
  return () => offlineQueue.sync(currentSession, ({ synced, failed, partial }) => {
    if (synced) {
      toast.success(t("synced", { count: synced }))
      qc.invalidateQueries({ queryKey: ["items"] })
      qc.invalidateQueries({ queryKey: ["tags"] })
    }
    if (failed) toast.error(t("syncFailed"))
    for (const id of partial) toast.warning(t("partial"), {
      action: { label: t("openItem"), onClick: () => router.push(`/items/${id}`) },
    })
  }).catch(() => { toast.error(t("unavailable")) })
}

/** 掛在 App 外框，換頁不重建同步引擎。 */
export function OfflineStatus() {
  const t = useTranslations("offline")
  const online = useOnline()
  const owner = useAuthStore((s) => s.user?.id)
  const token = useAuthStore((s) => s.accessToken)
  const sync = useOfflineSync()
  const error = useOfflineState((s) => s.error)
  useEffect(() => {
    void refreshOffline()
    if (owner && token) void sync()
    const onOnline = () => { if (currentSession()) void sync() }
    window.addEventListener("online", onOnline)
    return () => window.removeEventListener("online", onOnline)
    // 同步回呼只讀取最新 session，不因 toast／query client 的 render 重新啟動。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [owner, token])
  return (
    <div aria-live="polite" className="min-w-0 break-words">
      {!online && <p className="bg-muted px-4 py-2 text-sm text-muted-foreground">{t("banner")}</p>}
      {error && <p role="alert" className="px-4 py-2 text-sm text-destructive">{t(error)}</p>}
    </div>
  )
}

export function PendingBadge() {
  const rows = usePendingItems()
  const t = useTranslations("offline")
  return rows.length ? <Badge variant="secondary" className="ml-1 tabular-nums" aria-label={t("count", { count: rows.length })}>{rows.length}</Badge> : null
}
