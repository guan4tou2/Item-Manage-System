"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import {
  usePreferences,
  useUpdatePreferences,
} from "@/lib/preferences/use-preferences"

type ReportKind = "monthly" | "weekly"

/** 定期報表設定（Phase 31 月報、Phase 42 週報）：兩個獨立開關＋排程說明。 */
export function ReportsPanel() {
  const t = useTranslations("settings.reports")
  const prefs = usePreferences()
  const update = useUpdatePreferences()

  if (prefs.isLoading) {
    return (
      <div aria-busy="true" aria-label={t("loading")} className="space-y-4">
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (prefs.isError || !prefs.data) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
        <p className="text-muted-foreground text-sm">{t("loadError")}</p>
        <Button variant="outline" size="sm" onClick={() => void prefs.refetch()}>
          {t("retry")}
        </Button>
      </div>
    )
  }

  const monthlyEnabled = prefs.data.report_monthly_enabled
  const weeklyEnabled = prefs.data.report_weekly_enabled

  async function onToggle(kind: ReportKind, checked: boolean) {
    const body =
      kind === "monthly"
        ? { report_monthly_enabled: checked }
        : { report_weekly_enabled: checked }
    const key =
      kind === "monthly"
        ? checked
          ? "monthlySavedOn"
          : "monthlySavedOff"
        : checked
          ? "weeklySavedOn"
          : "weeklySavedOff"

    try {
      await update.mutateAsync(body)
      toast.success(t(key))
    } catch {
      toast.error(t("saveFailed"))
    }
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle className="text-base">{t("title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <section className="space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <p className="text-sm font-medium">{t("toggleTitle")}</p>
              <p className="text-muted-foreground text-sm">
                {t("toggleDescription")}
              </p>
            </div>
            <Switch
              aria-label={t("toggleTitle")}
              checked={monthlyEnabled}
              className="relative before:absolute before:inset-x-0 before:-inset-y-2.5 before:content-['']"
              disabled={update.isPending}
              onCheckedChange={(checked) => void onToggle("monthly", checked)}
            />
          </div>
          <p
            className="text-muted-foreground text-xs"
            data-testid="report-schedule-note"
          >
            {t("scheduleNote")}
          </p>
        </section>

        <section className="space-y-3 border-t pt-4">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <p className="text-sm font-medium">{t("weeklyTitle")}</p>
              <p className="text-muted-foreground text-sm">
                {t("weeklyDescription")}
              </p>
            </div>
            <Switch
              aria-label={t("weeklyTitle")}
              checked={weeklyEnabled}
              className="relative before:absolute before:inset-x-0 before:-inset-y-2.5 before:content-['']"
              disabled={update.isPending}
              onCheckedChange={(checked) => void onToggle("weekly", checked)}
            />
          </div>
          <p
            className="text-muted-foreground text-xs"
            data-testid="weekly-report-schedule-note"
          >
            {t("weeklyScheduleNote")}
          </p>
        </section>

        <Button asChild variant="outline" size="sm">
          <Link href="/reports">{t("historyLink")}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
