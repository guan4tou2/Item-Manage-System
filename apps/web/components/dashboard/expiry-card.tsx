"use client"

import { AlertCircle, CheckCircle2, ChevronRight, Clock } from "lucide-react"
import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { ExpiryStats } from "@/lib/api/stats"

interface Props {
  stats?: ExpiryStats
  loading?: boolean
  error?: boolean
  onRetry?: () => void
}

/** 儀表板到期行動卡（§5.1）：數字＋一句下一步（deep link）＋狀態註記。 */
export function ExpiryCard({ stats, loading, error, onRetry }: Props) {
  const t = useTranslations()
  const expiredCount = stats?.expired_count ?? 0
  const expiringCount = stats?.expiring_count ?? 0
  const soonest = stats?.items[0]

  return (
    <Card data-testid="expiry-card">
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.expiry.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <>
            <Skeleton className="h-12 w-full" data-testid="expiry-card-skeleton" />
            <Skeleton className="h-12 w-full" data-testid="expiry-card-skeleton" />
          </>
        ) : error ? (
          <div className="space-y-1" role="alert">
            <p className="text-sm text-muted-foreground">{t("dashboard.expiry.loadFailed")}</p>
            <Button
              type="button"
              variant="link"
              className="h-auto p-0"
              onClick={onRetry}
            >
              {t("dashboard.expiry.retry")}
            </Button>
          </div>
        ) : expiredCount === 0 && expiringCount === 0 ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground" data-status="ok">
            <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />
            {t("dashboard.expiry.allGood")}
          </p>
        ) : (
          <>
            {expiredCount > 0 ? (
              <Link
                href="/items?expiry=expired&sort=expiry_asc"
                className="flex min-h-11 items-center justify-between gap-3 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 hover:bg-destructive/10"
                data-status="expired"
              >
                <span className="flex items-center gap-2 text-sm font-medium text-destructive">
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  {t("dashboard.expiry.expired")}
                </span>
                <span className="flex items-center gap-1">
                  <span className="text-sm font-semibold tabular-nums text-destructive">
                    {t("dashboard.expiry.expiredCount", { count: expiredCount })}
                  </span>
                  <ChevronRight className="h-4 w-4 text-destructive" aria-hidden="true" />
                </span>
              </Link>
            ) : null}
            {expiringCount > 0 ? (
              <Link
                href="/items?expiry=expiring_soon&sort=expiry_asc"
                className="flex min-h-11 items-center justify-between gap-3 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 hover:bg-warning/20"
                data-status="expiring"
              >
                <span className="flex items-center gap-2 text-sm font-medium text-warning">
                  <Clock className="h-4 w-4" aria-hidden="true" />
                  {t("dashboard.expiry.expiringSoon")}
                </span>
                <span className="flex items-center gap-1">
                  <span className="text-sm font-semibold tabular-nums text-warning">
                    {t("dashboard.expiry.expiringSoonCount", { count: expiringCount })}
                  </span>
                  <ChevronRight className="h-4 w-4 text-warning" aria-hidden="true" />
                </span>
              </Link>
            ) : null}
            {soonest ? (
              <p className="text-xs text-muted-foreground" data-testid="expiry-card-note">
                {soonest.status === "expired"
                  ? t("dashboard.expiry.soonestExpired", {
                      name: soonest.name,
                      days: Math.abs(soonest.days_left ?? 0),
                    })
                  : t("dashboard.expiry.soonestExpiring", {
                      name: soonest.name,
                      days: soonest.days_left ?? 0,
                    })}
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  )
}
