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

/** 月報設定（Phase 31，D7／D9）：總開關＋排程說明＋歷史連結。 */
export function MonthlyReportPanel() {
  const t = useTranslations("settings.reports")
  const prefs = usePreferences()
  const update = useUpdatePreferences()

  if (prefs.isLoading) {
    return (
      <div aria-busy="true" aria-label={t("loading")} className="space-y-4">
        <Skeleton className="h-32 w-full" />
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

  const enabled = prefs.data.report_monthly_enabled

  async function onToggle(checked: boolean) {
    try {
      await update.mutateAsync({ report_monthly_enabled: checked })
      toast.success(checked ? t("savedOn") : t("savedOff"))
    } catch {
      toast.error(t("saveFailed"))
    }
  }

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle className="text-base">{t("toggleTitle")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <p className="text-muted-foreground text-sm">{t("toggleDescription")}</p>
          <Switch
            aria-label={t("toggleTitle")}
            checked={enabled}
            className="relative before:absolute before:inset-x-0 before:-inset-y-2.5 before:content-['']"
            disabled={update.isPending}
            onCheckedChange={(checked) => void onToggle(checked)}
          />
        </div>
        <p className="text-muted-foreground text-xs" data-testid="report-schedule-note">
          {t("scheduleNote")}
        </p>
        <Button asChild variant="outline" size="sm">
          <Link href="/reports">{t("historyLink")}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
