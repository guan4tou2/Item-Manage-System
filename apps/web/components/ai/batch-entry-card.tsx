"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { activeDraftTotal } from "@/lib/api/ai-drafts"
import { useDraftCounts } from "@/lib/hooks/use-ai-drafts"

/**
 * `/items/new` 的 AI 批次入庫入口（Phase 32 D9：入口不入首層導覽）。
 *
 * - 徽章僅計活動四態（pending／processing／ready／failed）；0 筆時不顯示
 * - 計數失敗不影響入口本身（僅少徽章），仍可前往佇列頁
 */
export function BatchEntryCard() {
  const t = useTranslations()
  const counts = useDraftCounts()
  const total = counts.data ? activeDraftTotal(counts.data) : 0

  return (
    <Card data-testid="batch-entry-card">
      <CardHeader className="pb-2">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          {t("items.new.batchEntry.title")}
          {counts.isLoading ? (
            <span className="text-xs font-normal text-muted-foreground">
              {t("items.new.batchEntry.badgeLoading")}
            </span>
          ) : null}
          {total > 0 ? (
            <Badge data-testid="batch-entry-badge" variant="secondary">
              {t("items.new.batchEntry.badge", { count: total })}
            </Badge>
          ) : null}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-xl text-sm text-muted-foreground">
          {t("items.new.batchEntry.description")}
        </p>
        <Button asChild size="sm" variant="outline">
          <Link href="/items/drafts">{t("items.new.batchEntry.cta")}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
