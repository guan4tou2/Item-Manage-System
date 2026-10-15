"use client"

import { useTranslations } from "next-intl"

import { cn } from "@/lib/utils"

const MS_PER_DAY = 86_400_000

/** Asia/Taipei 的「今天」ISO 日期（與後端 clock.py 同一時區定義）。 */
export function taipeiTodayIso(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now)
}

/** 距離到期日天數（負數＝已過期）；以 Asia/Taipei 今天為基準。 */
export function daysUntil(iso: string, now: Date = new Date()): number {
  const target = Date.parse(`${iso}T00:00:00Z`)
  const today = Date.parse(`${taipeiTodayIso(now)}T00:00:00Z`)
  return Math.round((target - today) / MS_PER_DAY)
}

interface Props {
  date: string
  className?: string
  /** 天數 > 7 時的呈現：顯示中性日期文字（預設）或完全不渲染。 */
  fallback?: "date" | "none"
}

/** 到期 badge（§5.6）：已過期紅／7 天內橙／其餘中性且不只用顏色表達。 */
export function ExpiryBadge({ date, className, fallback = "date" }: Props) {
  const t = useTranslations()
  const days = daysUntil(date)

  if (days < 0) {
    return (
      <span
        data-status="expired"
        className={cn(
          "inline-flex items-center rounded bg-destructive/10 px-1.5 py-0.5 text-xs font-medium text-destructive",
          className,
        )}
      >
        {t("items.batches.expiredDays", { days: Math.abs(days) })}
      </span>
    )
  }

  if (days <= 7) {
    return (
      <span
        data-status="expiring"
        className={cn(
          "inline-flex items-center rounded bg-warning/10 px-1.5 py-0.5 text-xs font-medium text-warning",
          className,
        )}
      >
        {days === 0 ? t("items.batches.expiresToday") : t("items.batches.daysLeft", { days })}
      </span>
    )
  }

  if (fallback === "none") return null
  return <span data-status="ok" className={cn("text-xs text-muted-foreground", className)}>{date}</span>
}
