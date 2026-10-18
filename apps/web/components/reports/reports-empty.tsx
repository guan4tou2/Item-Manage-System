"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { FileText } from "lucide-react"

import { Button } from "@/components/ui/button"

interface Props {
  /** 月報總開關關閉 → 顯示關閉說明與設定頁連結；否則顯示首月說明。 */
  disabled?: boolean
}

/** 報表清單空狀態（Phase 31，D9）。 */
export function ReportsEmpty({ disabled = false }: Props) {
  const t = useTranslations("reports.empty")
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
      <FileText className="text-muted-foreground h-8 w-8" aria-hidden="true" />
      <p className="text-sm font-medium">{disabled ? t("disabled") : t("title")}</p>
      <p className="text-muted-foreground text-sm">
        {disabled ? t("disabledHint") : t("firstMonth")}
      </p>
      {disabled && (
        <Button asChild variant="outline" size="sm">
          <Link href="/settings/reports">{t("openSettings")}</Link>
        </Button>
      )}
    </div>
  )
}
