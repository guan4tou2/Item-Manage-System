"use client"

import type { Route } from "next"
import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

/**
 * Phase 30（§5.5）：唯讀 viewer 直達編輯頁時取代表單的提示卡。
 * 不渲染表單本身（非僅禁用），並提供返回連結。
 */
export function ViewerNotice({
  backHref,
  backLabel,
}: {
  backHref: string
  backLabel: string
}) {
  const t = useTranslations()
  return (
    <div
      data-testid="viewer-notice"
      role="status"
      className="max-w-xl rounded-md border bg-muted p-6 text-center"
    >
      <p className="font-medium">{t("viewer.notice.title")}</p>
      <p className="mt-1 text-sm text-muted-foreground">{t("viewer.itemNotice")}</p>
      <Button asChild variant="link">
        <Link href={backHref as Route}>{backLabel}</Link>
      </Button>
    </div>
  )
}
