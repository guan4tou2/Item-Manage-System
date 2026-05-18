"use client"

import { useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import type { BulkImportSummary } from "@/lib/api/items-bulk"
import { downloadItemsCsv, importItemsCsv } from "@/lib/api/items-bulk"
import { useAccessToken } from "@/lib/auth/use-auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function CsvPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [exporting, setExporting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [summary, setSummary] = useState<BulkImportSummary | null>(null)

  async function handleExport() {
    setExporting(true)
    try {
      await downloadItemsCsv(token)
      toast.success(t("settings.csv.toast.exportDone"))
    } catch {
      toast.error(t("settings.csv.toast.exportFailed"))
    } finally {
      setExporting(false)
    }
  }

  async function handleImport(file: File) {
    setImporting(true)
    setSummary(null)
    try {
      const result = await importItemsCsv(file, token)
      setSummary(result)
      if (result.created_count > 0) {
        toast.success(t("settings.csv.toast.imported", { count: result.created_count }))
        qc.invalidateQueries({ queryKey: ["items"] })
        qc.invalidateQueries({ queryKey: ["stats"] })
      } else if (result.errors.length > 0) {
        toast.error(t("settings.csv.toast.importFailedWithErrors"))
      }
    } catch {
      toast.error(t("settings.csv.toast.importFailed"))
    } finally {
      setImporting(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("settings.csv.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>
            {t("settings.csv.exportDescription")}
            <code className="mx-1 rounded bg-muted px-1">id, name, description, quantity, min_quantity, category_name, location_floor/room/zone, warehouse_name, notes, is_favorite, created_at, updated_at</code>
          </p>
          <p>
            {t("settings.csv.importDescription")}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            {exporting ? t("settings.csv.exporting") : t("settings.csv.downloadCsv")}
          </Button>
          <Button
            onClick={() => fileRef.current?.click()}
            disabled={importing}
          >
            {importing ? t("settings.csv.importing") : t("settings.csv.selectCsvImport")}
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void handleImport(f)
            }}
          />
        </div>

        {summary ? (
          <div className="rounded border bg-muted/30 p-3 text-sm">
            <div>
              {t("settings.csv.summary.totalRows")}<strong>{summary.total_rows}</strong>
              {" "}{t("settings.csv.summary.created")}<strong>{summary.created_count}</strong>
              {" "}{t("settings.csv.summary.failed")}
              <strong className={summary.errors.length > 0 ? "text-destructive" : ""}>
                {summary.errors.length}
              </strong>
            </div>
            {summary.errors.length > 0 ? (
              <ul className="mt-2 space-y-0.5">
                {summary.errors.slice(0, 10).map((e: { row: number; reason: string }) => (
                  <li key={`${e.row}-${e.reason}`} className="font-mono text-xs">
                    {t("settings.csv.summary.errorRow", { row: e.row, reason: e.reason })}
                  </li>
                ))}
                {summary.errors.length > 10 ? (
                  <li className="text-xs text-muted-foreground">
                    {t("settings.csv.summary.moreErrors", { count: summary.errors.length - 10 })}
                  </li>
                ) : null}
              </ul>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
