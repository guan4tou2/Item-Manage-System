"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { FileText } from "lucide-react"

import { Button } from "@/components/ui/button"

interface Props {
  /** 月報總開關；預設開啟。 */
  monthlyEnabled?: boolean
  /** 週報總開關；預設關閉（opt-in）。 */
  weeklyEnabled?: boolean
}

/** 報表清單空狀態（Phase 31 月報、Phase 42 週報）。 */
export function ReportsEmpty({
  monthlyEnabled = true,
  weeklyEnabled = false,
}: Props) {
  const t = useTranslations("reports.empty")
  const bothDisabled = !monthlyEnabled && !weeklyEnabled
  const weeklyOnly = !monthlyEnabled && weeklyEnabled

  const title = bothDisabled
    ? t("disabled")
    : weeklyOnly
      ? t("weeklyOnly")
      : t("title")
  const hint = bothDisabled
    ? t("disabledHint")
    : weeklyOnly
      ? t("weeklyOnlyHint")
      : t("firstMonth")

  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-sm border border-dashed p-12 text-center">
      <FileText className="text-muted-foreground h-8 w-8" aria-hidden="true" />
      <p className="text-sm font-medium">{title}</p>
      <p className="text-muted-foreground text-sm">{hint}</p>
      {(bothDisabled || weeklyOnly) && (
        <Button asChild variant="outline" size="sm">
          <Link href="/settings/reports">{t("openSettings")}</Link>
        </Button>
      )}
    </div>
  )
}
