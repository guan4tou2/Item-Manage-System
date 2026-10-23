"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useLocale, useTranslations } from "next-intl"

import { ReportSummary } from "@/components/reports/report-summary"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiError } from "@/lib/api/client"
import type { ReportRead } from "@/lib/api/reports"
import { formatPeriod, formatPeriodRange } from "@/lib/format/period"
import { useReport } from "@/lib/hooks/use-reports"

export default function ReportDetailPage() {
  const t = useTranslations("reports")
  const locale = useLocale()
  const params = useParams()
  const reportId = String(params.id)
  const report = useReport(reportId)

  const notFound = report.error instanceof ApiError && report.error.status === 404

  function reportLabel(data: ReportRead): string {
    return data.kind === "weekly"
      ? formatPeriodRange(
          data.payload.period_start,
          data.payload.period_end,
          locale,
        )
      : formatPeriod(data.period, locale)
  }

  function renderBack() {
    return (
      <Button asChild variant="outline" size="sm">
        <Link href="/reports">{t("detail.back")}</Link>
      </Button>
    )
  }

  function renderContent() {
    if (report.isLoading) {
      return (
        <div aria-busy="true" aria-label={t("loading")} className="space-y-4">
          <Skeleton className="h-8 w-56" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-40 w-full sm:col-span-2" />
            <Skeleton className="h-40 w-full sm:col-span-2" />
          </div>
        </div>
      )
    }

    if (notFound) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
          <p className="text-muted-foreground text-sm">{t("detail.notFound")}</p>
          {renderBack()}
        </div>
      )
    }

    if (report.isError || !report.data) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
          <p className="text-muted-foreground text-sm">{t("detail.loadError")}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => void report.refetch()}>
              {t("detail.retry")}
            </Button>
            {renderBack()}
          </div>
        </div>
      )
    }

    const data = report.data
    const isWeekly = data.kind === "weekly"
    return (
      <ReportSummary
        payload={data.payload}
        heading={t(
          isWeekly ? "detail.headingWeekly" : "detail.heading",
          { period: reportLabel(data) },
        )}
      />
    )
  }

  return (
    <section className="space-y-6 p-4 sm:p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/reports">{t("title")}</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>
              {report.data ? reportLabel(report.data) : t("title")}
            </BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      {renderContent()}
    </section>
  )
}
