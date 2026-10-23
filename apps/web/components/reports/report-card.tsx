"use client"

import Link from "next/link"
import { useLocale, useTranslations } from "next-intl"
import { ChevronRight } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import type { ReportRead } from "@/lib/api/reports"
import { formatCurrency } from "@/lib/format/currency"
import { formatPeriod, formatPeriodRange } from "@/lib/format/period"

interface Props {
  report: ReportRead
}

/** 報表清單的週期卡（Phase 31 月報、Phase 42 週報）。 */
export function ReportCard({ report }: Props) {
  const t = useTranslations("reports")
  const locale = useLocale()
  const { payload } = report
  const isWeekly = report.kind === "weekly"
  const periodLabel = isWeekly
    ? formatPeriodRange(payload.period_start, payload.period_end, locale)
    : formatPeriod(report.period, locale)
  const generatedAt = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(report.generated_at))

  return (
    <Link
      href={`/reports/${report.id}`}
      className="focus-visible:ring-ring block rounded-lg focus-visible:ring-2 focus-visible:outline-none"
    >
      <Card className="hover:bg-accent/50 transition-colors">
        <CardContent className="flex items-center justify-between gap-4 py-4">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium">{periodLabel}</p>
              {isWeekly && (
                <Badge variant="outline">{t("weeklyBadge")}</Badge>
              )}
              {!payload.has_activity && (
                <Badge variant="secondary">
                  {t(isWeekly ? "noActivityWeekly" : "noActivity")}
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground text-sm" data-testid="report-summary">
              {t("detail.itemsUnit", { count: payload.totals.item_count })} ·{" "}
              {t("summary.created", { count: payload.activity.items_created })} ·{" "}
              {t("summary.used", { count: payload.activity.quantity_out })} ·{" "}
              {t("summary.value", {
                value: formatCurrency(payload.valuation.delta, payload.currency, locale),
              })}
            </p>
            <p
              className="text-muted-foreground text-xs"
              data-testid="report-generated-at"
            >
              {t("generatedAt", { time: generatedAt })}
            </p>
          </div>
          <span className="text-muted-foreground flex shrink-0 items-center gap-1 text-sm">
            {t("viewDetail")}
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </span>
        </CardContent>
      </Card>
    </Link>
  )
}
