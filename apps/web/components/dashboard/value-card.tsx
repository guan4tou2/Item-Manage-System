"use client"

import { ChevronRight } from "lucide-react"
import Link from "next/link"
import { useLocale, useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { ValueStats } from "@/lib/api/stats"
import { formatCurrency } from "@/lib/format/currency"

interface Props {
  stats?: ValueStats
  loading?: boolean
  error?: boolean
  onRetry?: () => void
}

/** 儀表板庫存估值卡（§5.1）：掛在行動卡最後；全無成本時引導補成本。 */
export function ValueCard({ stats, loading, error, onRetry }: Props) {
  const t = useTranslations()
  const locale = useLocale()
  const hasCosts = (stats?.priced_items ?? 0) > 0

  return (
    <Card data-testid="value-card">
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.value.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <Skeleton className="h-12 w-full" data-testid="value-card-skeleton" />
        ) : error ? (
          <div className="space-y-1" role="alert">
            <p className="text-sm text-muted-foreground">{t("dashboard.value.loadFailed")}</p>
            <Button type="button" variant="link" className="h-auto p-0" onClick={onRetry}>
              {t("dashboard.value.retry")}
            </Button>
          </div>
        ) : (
          <>
            <p className="text-2xl font-semibold tabular-nums" data-testid="value-card-amount">
              {formatCurrency(stats?.total_value ?? "0", stats?.currency ?? "TWD", locale)}
            </p>
            {hasCosts ? (
              <p className="text-sm text-muted-foreground">
                {t("dashboard.value.unpricedNote", {
                  unpriced: stats?.unpriced_items ?? 0,
                  total: stats?.total_items ?? 0,
                })}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">{t("dashboard.value.emptyNote")}</p>
            )}
            <Link
              href={hasCosts ? ("/statistics" as never) : ("/items" as never)}
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              data-testid="value-card-link"
            >
              {hasCosts ? t("dashboard.value.viewStats") : t("dashboard.value.goFill")}
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </>
        )}
      </CardContent>
    </Card>
  )
}
