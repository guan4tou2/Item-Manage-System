"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { NotificationsEmpty } from "@/components/notifications/empty"
import { NotificationItem } from "@/components/notifications/notification-item"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  useDeleteNotification,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/lib/hooks/use-notifications"
import type { NotificationRead } from "@/lib/api/notifications"
import {
  createRestockListFromLowStockItems,
  type RestockListItem,
} from "@/lib/api/lists"
import { useAccessToken } from "@/lib/auth/use-auth"

function extractRestockItem(row: NotificationRead): RestockListItem | null {
  if (row.type !== "low_stock" || !row.link) return null

  const itemId = row.link.match(/^\/items\/([^/?#]+)/)?.[1]
  if (!itemId) return null

  const quotedName = row.title.match(/[「"](.+?)[」"]/)?.[1]
  const fallbackName = row.title
    .replace(/庫存不足|low stock|stock is low/gi, "")
    .replace(/[：:]/g, "")
    .trim()
  const body = row.body ?? ""
  const quantity = Number(
    body.match(/(?:目前數量|current quantity)\s*[：:]\s*(\d+)/i)?.[1] ?? 0,
  )
  const minQuantity = Number(
    body.match(/(?:提醒閾值|minimum|threshold|min quantity)\s*[：:]\s*(\d+)/i)?.[1] ?? 1,
  )

  return {
    item_id: itemId,
    name: quotedName ?? fallbackName ?? row.title,
    quantity,
    min_quantity: minQuantity,
    deficit: Math.max(1, minQuantity - quantity),
  }
}

export default function NotificationsPage() {
  const t = useTranslations()
  const router = useRouter()
  const token = useAccessToken()
  const [tab, setTab] = useState<"all" | "unread">("all")
  const [openingId, setOpeningId] = useState<string | null>(null)
  const [restockId, setRestockId] = useState<string | null>(null)
  const query = useNotifications({ unreadOnly: tab === "unread", limit: 50, offset: 0 })
  const markRead = useMarkNotificationRead()
  const markAllRead = useMarkAllNotificationsRead()
  const del = useDeleteNotification()

  const handleOpen = async (row: NotificationRead) => {
    setOpeningId(row.id)
    try {
      if (row.read_at === null) await markRead.mutateAsync(row.id)
      if (row.link) router.push(row.link as never)
    } finally {
      setOpeningId(null)
    }
  }

  const handleAddToRestock = async (row: NotificationRead) => {
    const item = extractRestockItem(row)
    if (!item) {
      toast.error(t("dashboard.lowStock.restockFailed"))
      return
    }

    setRestockId(row.id)
    try {
      const date = new Date().toISOString().slice(0, 10)
      const list = await createRestockListFromLowStockItems([item], token, {
        title: t("dashboard.lowStock.restockListTitle", { date }),
      })
      toast.success(t("dashboard.lowStock.restockCreated"))
      router.push(`/lists/${list.id}` as never)
    } catch {
      toast.error(t("dashboard.lowStock.restockFailed"))
    } finally {
      setRestockId(null)
    }
  }

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/dashboard">{t("nav.dashboard")}</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{t("notifications.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("notifications.title")}</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending}
        >
          {t("notifications.actions.markAllRead")}
        </Button>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "all" | "unread")}>
        <TabsList>
          <TabsTrigger value="all">{t("notifications.filters.all")}</TabsTrigger>
          <TabsTrigger value="unread">{t("notifications.filters.unread")}</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="rounded-lg border">
        {query.isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : query.data && query.data.items.length > 0 ? (
          <ul>
            {query.data.items.map((row) => (
              <NotificationItem
                key={row.id}
                row={row}
                opening={openingId === row.id}
                restockPending={restockId === row.id}
                onOpen={(item) => {
                  void handleOpen(item)
                }}
                onAddToRestock={(item) => {
                  void handleAddToRestock(item)
                }}
                onDelete={(id) => del.mutate(id)}
              />
            ))}
          </ul>
        ) : (
          <NotificationsEmpty />
        )}
      </div>
    </section>
  )
}
