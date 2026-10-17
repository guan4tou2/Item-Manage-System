"use client"

import { useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import type { BackupImportMode, BackupImportResult } from "@/lib/api/backup"
import { downloadBackup, importBackup } from "@/lib/api/backup"
import { getApiErrorDetail } from "@/lib/api/client"
import { useAccessToken } from "@/lib/auth/use-auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const MAX_ERRORS_SHOWN = 5

export function BackupPanel() {
  const t = useTranslations()
  const token = useAccessToken()
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [exporting, setExporting] = useState(false)

  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<BackupImportMode>("create_only")
  const [dryRunResult, setDryRunResult] = useState<BackupImportResult | null>(null)
  const [confirmText, setConfirmText] = useState("")
  const [busy, setBusy] = useState(false)
  const [hardError, setHardError] = useState<string | null>(null)
  const [result, setResult] = useState<BackupImportResult | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

  async function handleExport() {
    setExporting(true)
    try {
      await downloadBackup(token)
      toast.success(t("settings.backup.export.toast.done"))
    } catch {
      toast.error(t("settings.backup.export.toast.failed"))
    } finally {
      setExporting(false)
    }
  }

  async function handleDownloadFirst() {
    try {
      await downloadBackup(token)
      toast.success(t("settings.backup.export.toast.done"))
    } catch {
      toast.error(t("settings.backup.export.toast.failed"))
    }
  }

  async function runDryRun(nextFile: File, nextMode: BackupImportMode) {
    setBusy(true)
    setHardError(null)
    setImportError(null)
    setDryRunResult(null)
    setResult(null)
    try {
      const result = await importBackup(
        nextFile,
        { mode: nextMode, dryRun: true },
        token,
      )
      setDryRunResult(result)
    } catch (err) {
      setHardError(getApiErrorDetail(err) ?? t("settings.backup.import.hardError"))
      toast.error(t("settings.backup.import.hardError"))
    } finally {
      setBusy(false)
    }
  }

  async function handlePick(picked: File) {
    setFile(picked)
    setConfirmText("")
    await runDryRun(picked, mode)
  }

  async function handleModeChange(nextValue: string) {
    const nextMode = nextValue as BackupImportMode
    setMode(nextMode)
    setConfirmText("")
    if (file) {
      await runDryRun(file, nextMode)
    }
  }

  async function handleConfirm() {
    if (!file || !dryRunResult) return
    setBusy(true)
    setImportError(null)
    setResult(null)
    try {
      const applied = await importBackup(
        file,
        {
          mode,
          dryRun: false,
          ...(mode === "replace" ? { confirm: confirmText } : {}),
        },
        token,
      )
      setResult(applied)
      if (applied.status !== "error") {
        await queryClient.invalidateQueries()
      }
    } catch (err) {
      setImportError(getApiErrorDetail(err) ?? t("settings.backup.import.importFailed"))
      toast.error(t("settings.backup.import.importFailed"))
    } finally {
      setBusy(false)
    }
  }

  async function handleRecheck() {
    if (!file) return
    await runDryRun(file, mode)
  }

  const replaceReady = mode !== "replace" || confirmText === "REPLACE"

  /** 摘要「匯入後」：create_only＝現有＋建立＋加後綴；replace＝建立＋加後綴。 */
  function afterImport(row: BackupImportResult["entities"][number]) {
    return mode === "replace"
      ? row.created + row.renamed
      : row.existing + row.created + row.renamed
  }

  function entityLabel(entity: string) {
    return t(`settings.backup.entities.${entity}` as never)
  }

  function renderRowErrors(
    errors: BackupImportResult["errors"],
    errorsTotal: number,
  ) {
    if (errors.length === 0) return null
    return (
      <div className="space-y-1 text-sm">
        <p className="font-medium text-destructive">
          {t("settings.backup.import.errorsTitle")}
        </p>
        <ul className="space-y-0.5">
          {errors.slice(0, MAX_ERRORS_SHOWN).map((row, i) => (
            <li key={`${row.entity}-${row.index}-${i}`} className="font-mono text-xs">
              {t("settings.backup.import.errorRow", {
                entity: entityLabel(row.entity),
                index: row.index,
                message: row.message,
              })}
            </li>
          ))}
        </ul>
        {errorsTotal > MAX_ERRORS_SHOWN ? (
          <p className="text-xs text-muted-foreground">
            {t("settings.backup.import.moreErrors", {
              count: errorsTotal - MAX_ERRORS_SHOWN,
            })}
          </p>
        ) : null}
      </div>
    )
  }

  const appliedCreated = result
    ? result.entities.reduce((acc, row) => acc + row.created + row.renamed, 0)
    : 0

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{t("settings.backup.export.title")}</CardTitle>
          <CardDescription>{t("settings.backup.export.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleExport}
            disabled={exporting}
            className="max-sm:min-h-11"
          >
            {exporting
              ? t("settings.backup.export.preparing")
              : t("settings.backup.export.download")}
          </Button>
        </CardContent>
      </Card>

      <Card aria-busy={busy}>
        <CardHeader>
          <CardTitle>{t("settings.backup.import.title")}</CardTitle>
          <CardDescription>{t("settings.backup.import.description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              onClick={() => fileRef.current?.click()}
              disabled={busy}
              className="max-sm:min-h-11"
            >
              {t("settings.backup.import.selectFile")}
            </Button>
            {file ? (
              <span className="text-sm text-muted-foreground">{file.name}</span>
            ) : null}
            <input
              ref={fileRef}
              type="file"
              accept=".json,application/json"
              className="sr-only"
              onChange={(e) => {
                const picked = e.target.files?.[0]
                if (picked) void handlePick(picked)
              }}
            />
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">{t("settings.backup.import.modeLabel")}</p>
            <RadioGroup
              value={mode}
              onValueChange={(value) => {
                void handleModeChange(value)
              }}
              className="flex flex-wrap gap-4"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="create_only" id="backup-mode-create-only" />
                <Label htmlFor="backup-mode-create-only">
                  {t("settings.backup.import.modeCreateOnly")}
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="replace" id="backup-mode-replace" />
                <Label htmlFor="backup-mode-replace">
                  {t("settings.backup.import.modeReplace")}
                </Label>
              </div>
            </RadioGroup>
          </div>

          {hardError ? (
            <p role="alert" className="text-sm text-destructive">
              {hardError}
            </p>
          ) : null}

          {busy ? (
            <p className="text-sm text-muted-foreground">
              {t("settings.backup.import.analyzing")}
            </p>
          ) : null}

          {!file && !busy ? (
            <p className="text-sm text-muted-foreground">
              {t("settings.backup.import.empty")}
            </p>
          ) : null}

          {dryRunResult ? (
            <div className="space-y-4">
              <h3 className="text-sm font-medium">{t("settings.backup.summary.title")}</h3>

              {dryRunResult.entities.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {t("settings.backup.import.emptySummary")}
                </p>
              ) : (
                <div className="hidden overflow-x-auto md:block">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t("settings.backup.summary.entity")}</TableHead>
                        <TableHead className="text-right">
                          {t("settings.backup.summary.existing")}
                        </TableHead>
                        <TableHead className="text-right">
                          {t("settings.backup.summary.after")}
                        </TableHead>
                        <TableHead className="text-right">
                          {t("settings.backup.summary.created")}
                        </TableHead>
                        <TableHead className="text-right">
                          {t("settings.backup.summary.reused")}
                        </TableHead>
                        <TableHead className="text-right">
                          {t("settings.backup.summary.renamed")}
                        </TableHead>
                        <TableHead className="text-right">
                          {t("settings.backup.summary.skipped")}
                        </TableHead>
                        <TableHead className="text-right">
                          {t("settings.backup.summary.errors")}
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dryRunResult.entities.map((row) => (
                        <TableRow key={row.entity}>
                          <TableCell>{entityLabel(row.entity)}</TableCell>
                          <TableCell className="text-right">{row.existing}</TableCell>
                          <TableCell className="text-right">{afterImport(row)}</TableCell>
                          <TableCell className="text-right">{row.created}</TableCell>
                          <TableCell className="text-right">{row.reused}</TableCell>
                          <TableCell className="text-right">{row.renamed}</TableCell>
                          <TableCell className="text-right">{row.skipped}</TableCell>
                          <TableCell
                            className={
                              row.errors > 0
                                ? "text-right font-medium text-destructive"
                                : "text-right"
                            }
                          >
                            {row.errors}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {dryRunResult.entities.length > 0 ? (
                <ul data-testid="backup-summary-cards" className="space-y-2 md:hidden">
                  {dryRunResult.entities.map((row) => (
                    <li key={row.entity} className="rounded border p-3 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{entityLabel(row.entity)}</span>
                        <span className="text-muted-foreground">
                          {t("settings.backup.summary.mobileFlow", {
                            existing: row.existing,
                            after: afterImport(row),
                          })}
                        </span>
                      </div>
                      <dl className="mt-2 grid grid-cols-3 gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        <div className="flex items-center justify-between gap-1">
                          <dt>{t("settings.backup.summary.created")}</dt>
                          <dd className="font-medium text-foreground">{row.created}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-1">
                          <dt>{t("settings.backup.summary.reused")}</dt>
                          <dd className="font-medium text-foreground">{row.reused}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-1">
                          <dt>{t("settings.backup.summary.renamed")}</dt>
                          <dd className="font-medium text-foreground">{row.renamed}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-1">
                          <dt>{t("settings.backup.summary.skipped")}</dt>
                          <dd className="font-medium text-foreground">{row.skipped}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-1">
                          <dt>{t("settings.backup.summary.errors")}</dt>
                          <dd
                            className={
                              row.errors > 0
                                ? "font-medium text-destructive"
                                : "font-medium text-foreground"
                            }
                          >
                            {row.errors}
                          </dd>
                        </div>
                      </dl>
                    </li>
                  ))}
                </ul>
              ) : null}

              {dryRunResult.entities.length > 0 && mode === "replace" ? (
                <p className="text-xs text-muted-foreground">
                  {t("settings.backup.summary.replaceNote")}
                </p>
              ) : null}

              {dryRunResult.warnings.length > 0 ? (
                <div className="space-y-1 text-sm">
                  <p className="font-medium">
                    {t("settings.backup.import.warningsTitle")}
                  </p>
                  <ul className="list-disc space-y-0.5 pl-5 text-muted-foreground">
                    {dryRunResult.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {dryRunResult.reconciliation.length > 0 ? (
                <div className="space-y-1 rounded border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
                  <p className="font-medium text-amber-700 dark:text-amber-400">
                    {t("settings.backup.import.reconciliationTitle")}
                  </p>
                  <ul className="space-y-0.5">
                    {dryRunResult.reconciliation.map((row) => (
                      <li key={row.item_id}>
                        {t("settings.backup.import.reconciliationRow", {
                          name: row.name,
                          quantity: row.quantity,
                          batch_total: row.batch_total,
                        })}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {renderRowErrors(dryRunResult.errors, dryRunResult.errors_total)}

              {mode === "replace" ? (
                <div className="space-y-2 rounded border border-destructive/50 bg-destructive/10 p-3">
                  <p className="text-sm font-medium text-destructive">
                    {t("settings.backup.replace.warning", {
                      count: dryRunResult.deleted_total,
                    })}
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => {
                      void handleDownloadFirst()
                    }}
                    className="max-sm:min-h-11"
                  >
                    {t("settings.backup.replace.downloadFirst")}
                  </Button>
                </div>
              ) : null}

              <div className="space-y-2">
                {mode === "replace" ? (
                  <div className="space-y-1">
                    <Label htmlFor="backup-confirm">
                      {t("settings.backup.replace.confirmLabel")}
                    </Label>
                    <Input
                      id="backup-confirm"
                      value={confirmText}
                      placeholder="REPLACE"
                      autoComplete="off"
                      onChange={(e) => setConfirmText(e.target.value)}
                      className="max-w-xs"
                    />
                  </div>
                ) : null}
                <Button
                  disabled={busy || !replaceReady}
                  onClick={() => {
                    void handleConfirm()
                  }}
                  className="max-sm:min-h-11"
                >
                  {t("settings.backup.import.confirm")}
                </Button>
              </div>

              {importError ? (
                <p role="alert" className="text-sm text-destructive">
                  {importError}
                </p>
              ) : null}

              {result ? (
                <div
                  role="status"
                  data-status={result.status}
                  className={`space-y-2 rounded border p-3 ${
                    result.status === "ok"
                      ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                      : result.status === "partial"
                        ? "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-400"
                        : "border-destructive/50 bg-destructive/10 text-destructive"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {result.status === "ok" ? (
                      <CheckCircle2 aria-hidden="true" className="size-4 shrink-0" />
                    ) : result.status === "partial" ? (
                      <AlertTriangle aria-hidden="true" className="size-4 shrink-0" />
                    ) : (
                      <XCircle aria-hidden="true" className="size-4 shrink-0" />
                    )}
                    <p className="text-sm font-medium">
                      {result.status === "ok"
                        ? t("settings.backup.result.ok", {
                            created: appliedCreated,
                            deleted: result.deleted_total,
                          })
                        : result.status === "partial"
                          ? t("settings.backup.result.partial", {
                              created: appliedCreated,
                              deleted: result.deleted_total,
                              errors: result.errors_total,
                            })
                          : t("settings.backup.result.error")}
                    </p>
                  </div>
                  {result.status !== "error" ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        void handleRecheck()
                      }}
                      className="max-sm:min-h-11"
                    >
                      {t("settings.backup.result.recheck")}
                    </Button>
                  ) : null}
                  {renderRowErrors(result.errors, result.errors_total)}
                </div>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
