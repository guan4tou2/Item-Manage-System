"use client"

import type { ReactNode } from "react"
import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { useMe } from "@/lib/hooks/use-profile"

/** admin-only 子頁守衛：載入中骨架、非 admin 空態（附返回設定）、權限查詢失敗可重試。 */
export function AdminOnly({ children }: { children: ReactNode }) {
  const t = useTranslations()
  const me = useMe()

  if (me.isLoading) {
    return (
      <div
        aria-busy="true"
        aria-label={t("settings.adminOnly.loading")}
        className="h-24 animate-pulse rounded-lg border bg-muted/40"
      />
    )
  }

  if (me.isError) {
    return (
      <div className="space-y-2 rounded-[0.25rem] border border-dashed p-4">
        <p className="text-sm text-muted-foreground">{t("settings.adminOnly.error")}</p>
        <Button size="sm" variant="outline" onClick={() => me.refetch()}>
          {t("settings.adminOnly.retry")}
        </Button>
      </div>
    )
  }

  if (me.data?.is_admin !== true) {
    return (
      <div className="space-y-2 rounded-[0.25rem] border border-dashed p-4">
        <p className="text-sm text-muted-foreground">{t("settings.adminOnly.prompt")}</p>
        <Button asChild size="sm" variant="outline">
          <Link href="/settings">{t("settings.adminOnly.back")}</Link>
        </Button>
      </div>
    )
  }

  return <>{children}</>
}
