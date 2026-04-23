"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

export function NotificationsEmpty() {
  const t = useTranslations()
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
      <p className="text-sm font-medium">{t("notifications.empty.title")}</p>
      <Button asChild variant="outline" size="sm">
        <Link href="/dashboard">{t("notifications.empty.cta")}</Link>
      </Button>
    </div>
  )
}
