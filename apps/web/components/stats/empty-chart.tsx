"use client"

import { useTranslations } from "next-intl"

export function EmptyChart() {
  const t = useTranslations()
  return (
    <div className="flex h-48 flex-col items-center justify-center rounded border border-dashed text-center">
      <p className="text-sm font-medium">{t("stats.empty.title")}</p>
      <p className="mt-1 text-xs text-muted-foreground">{t("stats.empty.cta")}</p>
    </div>
  )
}
