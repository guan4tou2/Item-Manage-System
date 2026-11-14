"use client"

import { Fragment, useEffect, useMemo, useState } from "react"
import { Download, Search, X } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { exportAuditLogs, type AuditFilters, type AuditLogRead } from "@/lib/api/audit"
import { useAccessToken } from "@/lib/auth/use-auth"
import { AUDIT_PAGE_SIZE, useAuditLogs } from "@/lib/hooks/use-audit-logs"

const ALL = "all"
const SEARCH_DEBOUNCE_MS = 300

/** 使用者選的當地日期 → 當日 00:00（UTC ISO）。 */
function localDayStartIso(value: string): string | undefined {
  if (!value) return undefined
  return new Date(`${value}T00:00:00`).toISOString()
}

/** 使用者選的當地日期 → 隔日 00:00（UTC ISO，含頭不含尾）。 */
function localDayEndIso(value: string): string | undefined {
  if (!value) return undefined
  const date = new Date(`${value}T00:00:00`)
  date.setDate(date.getDate() + 1)
  return date.toISOString()
}

function userLabel(row: AuditLogRead): string {
  if (row.user_email) return row.user_email
  if (row.user_id) return row.user_id.slice(0, 8)
  return "—"
}

function resourceLabel(row: AuditLogRead): string {
  if (!row.resource_id) return row.resource_type
  return `${row.resource_type} / ${row.resource_id.slice(0, 8)}`
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString()
}

export function AuditLogPanel() {
  const t = useTranslations()
  const token = useAccessToken()

  const [query, setQuery] = useState("")
  const [keyword, setKeyword] = useState("")
  const [action, setAction] = useState(ALL)
  const [resourceType, setResourceType] = useState(ALL)
  const [from, setFrom] = useState("")
  const [to, setTo] = useState("")
  const [offset, setOffset] = useState(0)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)
  const [exportFailed, setExportFailed] = useState(false)

  // 關鍵字 debounce；同時把頁碼歸零，避免「第 3 頁 + 新關鍵字」的空白頁
  useEffect(() => {
    const timer = setTimeout(() => {
      setKeyword(query.trim())
      setOffset(0)
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [query])

  const filters = useMemo<AuditFilters>(
    () => ({
      action: action === ALL ? undefined : action,
      resource_type: resourceType === ALL ? undefined : resourceType,
      q: keyword === "" ? undefined : keyword,
      created_from: localDayStartIso(from),
      created_to: localDayEndIso(to),
    }),
    [action, resourceType, keyword, from, to],
  )

  const page = useMemo(() => ({ limit: AUDIT_PAGE_SIZE, offset }), [offset])
  const logs = useAuditLogs(filters, page)

  const rows = logs.data?.items ?? []
  const total = logs.data?.total ?? 0
  const facets = logs.data?.facets
  const pages = Math.max(1, Math.ceil(total / AUDIT_PAGE_SIZE))
  const pageNumber = Math.floor(offset / AUDIT_PAGE_SIZE) + 1
  const hasFilters =
    keyword !== "" ||
    action !== ALL ||
    resourceType !== ALL ||
    from !== "" ||
    to !== ""

  function pickAction(value: string) {
    setAction(value)
    setOffset(0)
    setExpandedId(null)
  }

  function pickResourceType(value: string) {
    setResourceType(value)
    setOffset(0)
    setExpandedId(null)
  }

  function pickFrom(value: string) {
    setFrom(value)
    setOffset(0)
  }

  function pickTo(value: string) {
    setTo(value)
    setOffset(0)
  }

  function clearFilters() {
    setQuery("")
    setKeyword("")
    setAction(ALL)
    setResourceType(ALL)
    setFrom("")
    setTo("")
    setOffset(0)
    setExpandedId(null)
  }

  async function handleExport() {
    setExporting(true)
    setExportFailed(false)
    try {
      const { blob, filename } = await exportAuditLogs(filters, token)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch {
      setExportFailed(true)
    } finally {
      setExporting(false)
    }
  }

  // 目前篩選值不在 facets（例如超過前 50 名）時仍要能顯示
  const actionOptions = useMemo(() => {
    const options = [...(facets?.actions ?? [])]
    if (action !== ALL && !options.some((item) => item.value === action)) {
      options.push({ value: action, count: 0 })
    }
    return options
  }, [facets, action])
  const resourceOptions = useMemo(() => {
    const options = [...(facets?.resource_types ?? [])]
    if (
      resourceType !== ALL &&
      !options.some((item) => item.value === resourceType)
    ) {
      options.push({ value: resourceType, count: 0 })
    }
    return options
  }, [facets, resourceType])

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <div className="space-y-1.5 lg:col-span-2">
          <Label htmlFor="audit-search">{t("settings.audit.search")}</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="audit-search"
              className="pl-9"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t("settings.audit.searchPlaceholder")}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="audit-action">{t("settings.audit.action")}</Label>
          <Select value={action} onValueChange={pickAction}>
            <SelectTrigger id="audit-action" aria-label={t("settings.audit.action")}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t("settings.audit.allActions")}</SelectItem>
              {actionOptions.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="audit-resource">{t("settings.audit.resourceType")}</Label>
          <Select value={resourceType} onValueChange={pickResourceType}>
            <SelectTrigger
              id="audit-resource"
              aria-label={t("settings.audit.resourceType")}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>
                {t("settings.audit.allResourceTypes")}
              </SelectItem>
              {resourceOptions.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="audit-from">{t("settings.audit.from")}</Label>
          <Input
            id="audit-from"
            type="date"
            value={from}
            onChange={(event) => pickFrom(event.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="audit-to">{t("settings.audit.to")}</Label>
          <Input
            id="audit-to"
            type="date"
            value={to}
            onChange={(event) => pickTo(event.target.value)}
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-sm text-muted-foreground">
          {t("settings.audit.total", { count: total })}
        </span>
        <span aria-hidden className="text-muted-foreground">
          ·
        </span>
        <span className="text-sm text-muted-foreground">
          {t("settings.audit.page", { page: pageNumber, pages })}
        </span>
        <div className="ml-auto flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={clearFilters}
            disabled={!hasFilters}
          >
            <X />
            {t("settings.audit.clear")}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => void handleExport()}
            disabled={exporting || total === 0}
          >
            <Download />
            {exporting ? t("settings.audit.exporting") : t("settings.audit.export")}
          </Button>
        </div>
      </div>

      {exportFailed && (
        <p role="alert" className="text-sm text-destructive">
          {t("settings.audit.exportFailed")}
        </p>
      )}

      {logs.isError ? (
        <div
          role="alert"
          className="flex flex-wrap items-center gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm"
        >
          <span>{t("settings.audit.loadFailed")}</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void logs.refetch()}
          >
            {t("settings.audit.retry")}
          </Button>
        </div>
      ) : logs.isLoading ? (
        <div className="space-y-2" aria-busy="true">
          <span className="sr-only">{t("settings.audit.loading")}</span>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : total === 0 ? (
        <p className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          {hasFilters
            ? t("settings.audit.noMatches")
            : t("settings.audit.empty")}
        </p>
      ) : (
        <>
          <div data-testid="audit-table" className="hidden rounded-md border md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("settings.audit.colTime")}</TableHead>
                  <TableHead>{t("settings.audit.colUser")}</TableHead>
                  <TableHead>{t("settings.audit.colAction")}</TableHead>
                  <TableHead>{t("settings.audit.colResource")}</TableHead>
                  <TableHead>{t("settings.audit.colMeta")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <Fragment key={row.id}>
                    <TableRow>
                      <TableCell className="whitespace-nowrap text-xs">
                        {formatTime(row.created_at)}
                      </TableCell>
                      <TableCell className="text-xs">{userLabel(row)}</TableCell>
                      <TableCell>
                        <span className="font-mono text-xs">{row.action}</span>
                      </TableCell>
                      <TableCell className="text-xs">
                        {resourceLabel(row)}
                      </TableCell>
                      <TableCell className="text-xs">
                        {row.meta ? (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            aria-expanded={expandedId === row.id}
                            onClick={() =>
                              setExpandedId(
                                expandedId === row.id ? null : row.id,
                              )
                            }
                          >
                            {expandedId === row.id
                              ? t("settings.audit.hideDetails")
                              : t("settings.audit.details")}
                          </Button>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                    </TableRow>
                    {expandedId === row.id && (
                      <TableRow>
                        <TableCell colSpan={5}>
                          <pre
                            data-testid="audit-meta-json"
                            className="max-h-64 overflow-auto rounded-sm bg-muted p-3 text-xs"
                          >
                            {JSON.stringify(row.meta, null, 2)}
                          </pre>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </div>

          <ul className="space-y-3 md:hidden">
            {rows.map((row) => (
              <li
                key={row.id}
                data-testid="audit-card"
                className="rounded-md border p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs">{row.action}</span>
                  <time className="whitespace-nowrap text-xs text-muted-foreground">
                    {formatTime(row.created_at)}
                  </time>
                </div>
                <p className="mt-1 text-sm">{userLabel(row)}</p>
                <p className="text-xs text-muted-foreground">
                  {resourceLabel(row)}
                </p>
                {row.meta && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-muted-foreground">
                      {t("settings.audit.colMeta")}
                    </summary>
                    <pre className="mt-1 max-h-40 overflow-auto rounded-sm bg-muted p-2 text-xs">
                      {JSON.stringify(row.meta, null, 2)}
                    </pre>
                  </details>
                )}
              </li>
            ))}
          </ul>

          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setOffset(Math.max(0, offset - AUDIT_PAGE_SIZE))}
              disabled={offset === 0}
            >
              {t("settings.audit.prev")}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setOffset(offset + AUDIT_PAGE_SIZE)}
              disabled={offset + AUDIT_PAGE_SIZE >= total}
            >
              {t("settings.audit.next")}
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
