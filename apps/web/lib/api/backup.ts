import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type BackupImportResult =
  paths["/api/backup/import"]["post"]["responses"]["200"]["content"]["application/json"]

export type BackupImportMode = "create_only" | "replace"

export interface BackupImportOptions {
  mode: BackupImportMode
  dryRun: boolean
  /** replace 且非 dry-run 時必填（固定 `REPLACE`） */
  confirm?: string
}

/** Downloads the JSON backup by streaming the Blob into an object URL and clicking. */
export async function downloadBackup(accessToken: string | null): Promise<void> {
  const res = await apiFetch("/backup/export", { accessToken })
  const blob = await res.blob()
  const disposition = res.headers.get("Content-Disposition") ?? ""
  const match = /filename="?([^";]+)"?/.exec(disposition)
  const filename = match?.[1] ?? "ims-backup.json"
  const url = URL.createObjectURL(blob)
  try {
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
  } finally {
    // Defer revoke slightly so the browser can start the download
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

export async function importBackup(
  file: File,
  options: BackupImportOptions,
  accessToken: string | null,
): Promise<BackupImportResult> {
  const form = new FormData()
  form.append("file", file)
  form.append("mode", options.mode)
  form.append("dry_run", options.dryRun ? "true" : "false")
  if (!options.dryRun && options.mode === "replace" && options.confirm) {
    form.append("confirm", options.confirm)
  }
  const res = await apiFetch("/backup/import", {
    method: "POST",
    body: form,
    accessToken,
  })
  return (await res.json()) as BackupImportResult
}
