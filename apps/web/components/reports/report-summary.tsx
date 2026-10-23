"use client"

import { useLocale, useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ReportPayload } from "@/lib/api/reports"
import { formatCurrency } from "@/lib/format/currency"

interface Props {
  payload: ReportPayload
  /** 週期標題（已在地化），用於頁首。 */
  heading: string
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="space-y-0.5">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="text-lg font-semibold tabular-nums">{value}</p>
    </div>
  )
}

/** 報表詳情內容（Phase 31 月報、Phase 42 週報）：庫存現況／動態／到期／估值／熱門分類位置。 */
export function ReportSummary({ payload, heading }: Props) {
  const t = useTranslations("reports.detail")
  const tReports = useTranslations("reports")
  const locale = useLocale()
  const isWeekly = payload.kind === "weekly"
  const money = (value: string) =>
    formatCurrency(value, payload.currency, locale)

  const delta = Number(payload.valuation.delta)
  const deltaClass =
    delta > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : delta < 0
        ? "text-destructive"
        : "text-muted-foreground"

  function bucketList(
    buckets: ReportPayload["top_categories"],
    fallback: string,
  ) {
    return (
      <ul className="space-y-1.5">
        {buckets.map((bucket, index) => (
          <li
            key={`${bucket.label ?? "none"}-${index}`}
            className="flex items-center justify-between gap-3 text-sm"
          >
            <span className="truncate">{bucket.label ?? fallback}</span>
            <span className="text-muted-foreground tabular-nums">
              {t("itemsUnit", { count: bucket.count })}
            </span>
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-semibold">{heading}</h1>
        {!payload.has_activity && (
          <Badge variant="secondary">
            {tReports(isWeekly ? "noActivityWeekly" : "noActivity")}
          </Badge>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card data-testid="report-inventory">
          <CardHeader>
            <CardTitle className="text-base">{t("inventory")}</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-2">
            <Metric label={t("items")} value={payload.totals.item_count} />
            <Metric label={t("quantity")} value={payload.totals.quantity} />
          </CardContent>
        </Card>

        <Card data-testid="report-expiry">
          <CardHeader>
            <CardTitle className="text-base">
              {t(isWeekly ? "expiryWeekly" : "expiry")}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <Metric label={t("expiringSoon")} value={payload.expiry.expiring_soon} />
            <Metric label={t("expired")} value={payload.expiry.expired} />
          </CardContent>
        </Card>

        <Card data-testid="report-activity" className="sm:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">
              {t(isWeekly ? "activityWeekly" : "activity")}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric label={t("created")} value={payload.activity.items_created} />
            <Metric label={t("deleted")} value={payload.activity.items_deleted} />
            <Metric label={t("qtyIn")} value={payload.activity.quantity_in} />
            <Metric label={t("qtyOut")} value={payload.activity.quantity_out} />
            <Metric label={t("loansOut")} value={payload.activity.loans_out} />
            <Metric label={t("loansReturned")} value={payload.activity.loans_returned} />
            <Metric label={t("loansOverdue")} value={payload.activity.loans_overdue} />
          </CardContent>
        </Card>

        <Card data-testid="report-valuation" className="sm:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">{t("valuation")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-4">
              <Metric
                label={t(isWeekly ? "startWeekly" : "start")}
                value={money(payload.valuation.start)}
              />
              <Metric
                label={t(isWeekly ? "endWeekly" : "end")}
                value={money(payload.valuation.end)}
              />
              <div className="space-y-0.5">
                <p className="text-muted-foreground text-xs">{t("delta")}</p>
                <p
                  className={`text-lg font-semibold tabular-nums ${deltaClass}`}
                  data-testid="report-valuation-delta"
                >
                  {delta > 0 ? "+" : ""}
                  {money(payload.valuation.delta)}
                </p>
              </div>
            </div>
            {payload.valuation.unpriced_items > 0 && (
              <p className="text-muted-foreground text-xs" data-testid="report-unpriced">
                {t("unpriced", { count: payload.valuation.unpriced_items })}
              </p>
            )}
          </CardContent>
        </Card>

        <Card data-testid="report-top-categories">
          <CardHeader>
            <CardTitle className="text-base">{t("topCategories")}</CardTitle>
          </CardHeader>
          <CardContent>
            {bucketList(payload.top_categories, t("uncategorized"))}
          </CardContent>
        </Card>

        <Card data-testid="report-top-locations">
          <CardHeader>
            <CardTitle className="text-base">{t("topLocations")}</CardTitle>
          </CardHeader>
          <CardContent>
            {bucketList(payload.top_locations, t("unassigned"))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
