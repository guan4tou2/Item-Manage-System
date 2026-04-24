"use client"

import { useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import type { BulkImportSummary } from "@/lib/api/items-bulk"
import { downloadItemsCsv, importItemsCsv } from "@/lib/api/items-bulk"
import { useAccessToken } from "@/lib/auth/use-auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function CsvPanel() {
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
      toast.success("匯出完成")
    } catch {
      toast.error("匯出失敗")
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
        toast.success(`已匯入 ${result.created_count} 筆`)
        qc.invalidateQueries({ queryKey: ["items"] })
        qc.invalidateQueries({ queryKey: ["stats"] })
      } else if (result.errors.length > 0) {
        toast.error("匯入失敗，請檢查錯誤列表")
      }
    } catch {
      toast.error("匯入失敗")
    } finally {
      setImporting(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>批次匯入 / 匯出</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>
            匯出 CSV 包含所有未刪除的物品；欄位：
            <code className="mx-1 rounded bg-muted px-1">id, name, description, quantity, min_quantity, category_name, location_floor/room/zone, warehouse_name, notes, is_favorite, created_at, updated_at</code>
          </p>
          <p>
            匯入支援 <code>name</code>（必填）、<code>quantity</code>、<code>min_quantity</code>、
            <code>description</code>、<code>notes</code>、<code>category_name</code>、
            <code>location_floor/room/zone</code>、<code>warehouse_name</code>。分類 / 位置 / 倉庫若不存在會自動建立。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            {exporting ? "匯出中…" : "下載 CSV"}
          </Button>
          <Button
            onClick={() => fileRef.current?.click()}
            disabled={importing}
          >
            {importing ? "匯入中…" : "選擇 CSV 匯入"}
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
              總列數：<strong>{summary.total_rows}</strong>
              成功建立：<strong>{summary.created_count}</strong>
              失敗：
              <strong className={summary.errors.length > 0 ? "text-destructive" : ""}>
                {summary.errors.length}
              </strong>
            </div>
            {summary.errors.length > 0 ? (
              <ul className="mt-2 space-y-0.5">
                {summary.errors.slice(0, 10).map((e) => (
                  <li key={`${e.row}-${e.reason}`} className="font-mono text-xs">
                    第 {e.row} 列：{e.reason}
                  </li>
                ))}
                {summary.errors.length > 10 ? (
                  <li className="text-xs text-muted-foreground">
                    …還有 {summary.errors.length - 10} 筆錯誤
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
