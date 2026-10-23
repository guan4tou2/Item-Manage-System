"use client"

import { useTranslations } from "next-intl"

import { ReportCard } from "@/components/reports/report-card"
import { ReportsEmpty } from "@/components/reports/reports-empty"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { usePreferences } from "@/lib/preferences/use-preferences"
import { useReports } from "@/lib/hooks/use-reports"

export default function ReportsPage() {
  const t = useTranslations("reports")
  const reports = useReports()
  const prefs = usePreferences()

  function renderContent() {
    if (reports.isLoading) {
      return (
        <div aria-busy="true" aria-label={t("loading")} className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )
    }

    if (reports.isError) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
          <p className="text-muted-foreground text-sm">{t("loadError")}</p>
          <Button variant="outline" size="sm" onClick={() => void reports.refetch()}>
            {t("retry")}
          </Button>
        </div>
      )
    }

    const items = reports.data?.items ?? []
    if (items.length === 0) {
      return (
        <ReportsEmpty
          monthlyEnabled={prefs.data?.report_monthly_enabled !== false}
          weeklyEnabled={prefs.data?.report_weekly_enabled === true}
        />
      )
    }

    return (
      <ul className="space-y-3">
        {items.map((report) => (
          <li key={report.id}>
            <ReportCard report={report} />
          </li>
        ))}
      </ul>
    )
  }

  return (
    <section className="space-y-6 p-4 sm:p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-muted-foreground text-sm">{t("description")}</p>
      </div>
      {renderContent()}
    </section>
  )
}
