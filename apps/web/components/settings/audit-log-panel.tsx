"use client"
import { useQuery } from "@tanstack/react-query"
import { useTranslations } from "next-intl"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { apiFetch } from "@/lib/api/client"
import { useAccessToken } from "@/lib/auth/use-auth"

interface AuditLogRow {
  id: string
  user_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  meta: Record<string, unknown> | null
  created_at: string
}

async function listAuditLogs(token: string | null): Promise<AuditLogRow[]> {
  return (await apiFetch("/admin/audit-logs?limit=200", { accessToken: token })).json()
}

export function AuditLogPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const query = useQuery({
    queryKey: ["admin", "audit-logs"],
    queryFn: () => listAuditLogs(token),
    enabled: token !== null,
    staleTime: 30_000,
  })

  const rows = query.data ?? []
  if (query.isLoading) return <p className="text-sm text-muted-foreground">{t("settings.audit.loading")}</p>
  if (rows.length === 0) return <p className="text-sm text-muted-foreground">{t("settings.audit.empty")}</p>

  return (
    <div className="rounded border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("settings.audit.colTime")}</TableHead>
            <TableHead>{t("settings.audit.colUser")}</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Resource</TableHead>
            <TableHead>Meta</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="text-xs tabular-nums">
                {new Date(r.created_at).toLocaleString()}
              </TableCell>
              <TableCell className="text-xs">{r.user_id?.slice(0, 8) ?? "—"}</TableCell>
              <TableCell className="font-mono text-xs">{r.action}</TableCell>
              <TableCell className="text-xs">
                {r.resource_type}
                {r.resource_id ? ` / ${r.resource_id.slice(0, 8)}` : ""}
              </TableCell>
              <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                {r.meta ? JSON.stringify(r.meta) : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
