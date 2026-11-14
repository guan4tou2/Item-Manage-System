"use client"

import { useRouter } from "next/navigation"
import { useLocale, useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { editPending, offlineQueue, useOnline, usePendingItems } from "@/lib/offline/runtime"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useOfflineSync } from "./offline-status"

export function PendingItems() {
  const t = useTranslations("offline")
  const locale = useLocale()
  const rows = usePendingItems()
  const online = useOnline()
  const readOnly = useReadOnly()
  const router = useRouter()
  const sync = useOfflineSync()
  const [busy, setBusy] = useState(false)
  if (!rows.length) return null
  return (
    <section className="min-w-0 rounded-lg border bg-muted/50 p-4" aria-label={t("count", { count: rows.length })}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold tabular-nums">{t("count", { count: rows.length })}</h2>
        <Button variant="outline" className="min-h-11" disabled={!online || busy} onClick={async () => { setBusy(true); try { await sync() } finally { setBusy(false) } }}>{t("syncNow")}</Button>
      </div>
      <details className="mt-2">
        <summary className="cursor-pointer py-3 text-sm">{t("details")}</summary>
        <ul className="divide-y">
          {rows.map((row) => (
            <li key={row.client_id} className="min-w-0 space-y-2 py-3">
              <p className="break-words text-sm font-medium [overflow-wrap:anywhere]">{row.values.name}</p>
              <p className="text-xs text-muted-foreground">{new Date(row.created_at).toLocaleString(locale)}</p>
              <Badge variant={row.status === "failed" ? "destructive" : "secondary"}>{t(row.status)}</Badge>
              {row.status === "failed" && <p className="break-words text-sm text-destructive">{t(`reason.${["location", "category", "403", "404", "409", "410", "422", "idempotent_item_deleted", "server"].includes(row.error_code ?? "") ? row.error_code : "unknown"}` as never)}</p>}
              <div className="flex flex-wrap gap-2">
                {!readOnly && <Button variant="outline" className="min-h-11" disabled={row.status === "syncing"} onClick={() => { editPending(row); router.push("/items/new") }}>{t("edit")}</Button>}
                <AlertDialog>
                  <AlertDialogTrigger asChild><Button variant="ghost" className="min-h-11" disabled={row.status === "syncing"}>{t("discard")}</Button></AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader><AlertDialogTitle>{t("discardTitle")}</AlertDialogTitle><AlertDialogDescription>{t("discardDescription")}</AlertDialogDescription></AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
                      <AlertDialogAction onClick={() => { void offlineQueue.remove(row.client_id).catch(() => toast.error(t("unavailable"))) }}>{t("discard")}</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
