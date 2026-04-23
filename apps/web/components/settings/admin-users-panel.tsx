"use client"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useAuthStore } from "@/lib/auth/auth-store"
import { useAdminUsers, useSendTestNotification, useSetUserActive } from "@/lib/hooks/use-admin"

export function AdminUsersPanel() {
  const t = useTranslations()
  const query = useAdminUsers(true)
  const setActive = useSetUserActive()
  const sendTest = useSendTestNotification()
  const currentUserId = useAuthStore((s) => s.user?.id ?? "")

  const onToggle = async (userId: string, isActive: boolean) => {
    try {
      await setActive.mutateAsync({ userId, isActive: !isActive })
    } catch (e: unknown) {
      const err = e as { body?: { detail?: string } }
      const detail = err.body?.detail ?? ""
      if (detail.includes("self")) toast.error(t("settings.admin.errors.cannotDeactivateSelf"))
      else if (detail.includes("last admin")) toast.error(t("settings.admin.errors.cannotRemoveLastAdmin"))
      else toast.error(detail || "error")
    }
  }

  const onSendTest = async (userId: string) => {
    await sendTest.mutateAsync(userId)
    toast.success(t("settings.admin.testSent"))
  }

  const rows = query.data ?? []
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("settings.admin.emptyTable")}</p>
  }

  return (
    <div className="rounded border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("settings.admin.cols.username")}</TableHead>
            <TableHead>{t("settings.admin.cols.email")}</TableHead>
            <TableHead>{t("settings.admin.cols.flags")}</TableHead>
            <TableHead className="text-right">{t("settings.admin.cols.actions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((u) => (
            <TableRow key={u.id}>
              <TableCell className="font-medium">{u.username}</TableCell>
              <TableCell>{u.email}</TableCell>
              <TableCell className="space-x-1">
                <Badge variant={u.is_active ? "default" : "secondary"}>
                  {u.is_active ? t("settings.admin.status.active") : t("settings.admin.status.inactive")}
                </Badge>
                {u.is_admin ? <Badge variant="outline">{t("settings.admin.status.admin")}</Badge> : null}
              </TableCell>
              <TableCell className="space-x-2 text-right">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onToggle(u.id, u.is_active)}
                  disabled={u.id === currentUserId}
                >
                  {u.is_active ? t("settings.admin.actions.deactivate") : t("settings.admin.actions.activate")}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => onSendTest(u.id)}>
                  {t("settings.admin.actions.sendTest")}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
