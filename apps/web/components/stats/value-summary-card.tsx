"use client"

import { useLocale, useTranslations } from "next-intl"

import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import type { ValueStats } from "@/lib/api/stats"
import { CURRENCY_SYMBOLS, formatCurrency, type Currency } from "@/lib/format/currency"

interface Props {
  data?: ValueStats
  loading?: boolean
}

export function ValueSummaryCard({ data, loading }: Props) {
  const t = useTranslations()
  const locale = useLocale()

  if (!data || loading) {
    return (
      <Card>
        <CardContent className="space-y-3 pt-6">
          <Skeleton className="h-8 w-40" data-testid="value-summary-skeleton" />
          <Skeleton className="h-4 w-56" />
        </CardContent>
      </Card>
    )
  }

  const symbol = CURRENCY_SYMBOLS[data.currency as Currency] ?? data.currency
  const pct =
    data.total_items > 0
      ? Math.round((data.unpriced_items / data.total_items) * 100)
      : 0

  return (
    <Card>
      <CardContent className="space-y-1 pt-6">
        <p className="text-3xl font-semibold tabular-nums" data-testid="value-summary">
          {formatCurrency(data.total_value, data.currency, locale)}
        </p>
        <p className="text-sm text-muted-foreground">
          {t("stats.value.pricedLine", {
            priced: data.priced_items,
            total: data.total_items,
          })}
        </p>
        {data.total_items > 0 && (
          <p className="text-sm text-muted-foreground">
            {t("stats.value.unpricedLine", {
              unpriced: data.unpriced_items,
              pct,
            })}
          </p>
        )}
        {data.unpriced_items > 0 && (
          <p className="text-xs text-muted-foreground">
            {t("stats.value.unpricedNote", { symbol })}
          </p>
        )}
        {data.priced_items === 0 && (
          <p className="text-sm">{t("stats.value.zeroTotal")}</p>
        )}
      </CardContent>
    </Card>
  )
}
