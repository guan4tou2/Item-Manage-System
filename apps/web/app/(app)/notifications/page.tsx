"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"

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

export default function NotificationsPage() {
  const t = useTranslations()
  const router = useRouter()
  const [tab, setTab] = useState<"all" | "unread">("all")
  const query = useNotifications({ unreadOnly: tab === "unread", limit: 50, offset: 0 })
  const markRead = useMarkNotificationRead()
  const markAllRead = useMarkAllNotificationsRead()
  const del = useDeleteNotification()

  const handleOpen = (row: NotificationRead) => {
    if (row.read_at === null) markRead.mutate(row.id)
    if (row.link) router.push(row.link as never)
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
                onOpen={handleOpen}
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
