"use client"

import Link from "next/link"
import { Bell } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { useUnreadCount } from "@/lib/hooks/use-notifications"

export function NotificationBell() {
  const t = useTranslations()
  const { data } = useUnreadCount()
  const count = data?.count ?? 0
  const label = count > 99 ? "99+" : String(count)

  return (
    <Button
      asChild
      variant="ghost"
      size="icon"
      aria-label={t("notifications.bell.label")}
      className="relative"
    >
      <Link href="/notifications">
        <Bell className="h-5 w-5" />
        {count > 0 ? (
          <span
            data-testid="notification-badge"
            aria-live="polite"
            className="absolute -right-1 -top-1 min-w-[1.25rem] rounded-full bg-destructive px-1 text-[0.625rem] font-semibold leading-4 text-destructive-foreground"
          >
            {label}
          </span>
        ) : null}
      </Link>
    </Button>
  )
}
