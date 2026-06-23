"use client"

import { ListPlus, Loader2, X } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { NotificationRead } from "@/lib/api/notifications"

interface Props {
  row: NotificationRead
  onOpen: (row: NotificationRead) => void
  onDelete: (id: string) => void
  onAddToRestock?: (row: NotificationRead) => void
  opening?: boolean
  restockPending?: boolean
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const sec = Math.max(0, Math.round(diffMs / 1000))
  if (sec < 60) return `${sec}s`
  const min = Math.round(sec / 60)
  if (min < 60) return `${min}m`
  const hr = Math.round(min / 60)
  if (hr < 24) return `${hr}h`
  const day = Math.round(hr / 24)
  return `${day}d`
}

export function NotificationItem({
  row,
  onOpen,
  onDelete,
  onAddToRestock,
  opening,
  restockPending,
}: Props) {
  const t = useTranslations()
  const unread = row.read_at === null
  const canAddToRestock = row.type === "low_stock" && onAddToRestock
  return (
    <li
      aria-label={row.title}
      aria-busy={opening || restockPending ? "true" : "false"}
      className={cn(
        "group flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-start",
        !unread && "opacity-70",
      )}
    >
      <button
        type="button"
        aria-label="Open notification"
        onClick={() => onOpen(row)}
        className="flex flex-1 flex-col items-start gap-1 text-left"
      >
        <div className="flex items-center gap-2">
          {unread ? (
            <span
              data-testid="unread-dot"
              aria-hidden
              className="h-2 w-2 rounded-full bg-primary"
            />
          ) : null}
          <span className="font-medium">{row.title}</span>
          <span className="text-xs text-muted-foreground">{formatRelative(row.created_at)}</span>
        </div>
        {row.body ? (
          <p className="text-sm text-muted-foreground">{row.body}</p>
        ) : null}
      </button>
      <div className="flex items-center justify-end gap-2">
        {canAddToRestock ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onAddToRestock(row)}
            disabled={restockPending}
          >
            {restockPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <ListPlus className="h-4 w-4" aria-hidden />
            )}
            {t("notifications.actions.addToRestockList")}
          </Button>
        ) : null}
        <Button
          variant="ghost"
          size="icon"
          aria-label={t("notifications.actions.delete")}
          onClick={() => onDelete(row.id)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </li>
  )
}
