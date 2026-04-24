import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type BulkImportSummary =
  paths["/api/items/bulk-import"]["post"]["responses"]["200"]["content"]["application/json"]

/** Downloads the CSV by streaming the Blob into an object URL and clicking. */
export async function downloadItemsCsv(accessToken: string | null): Promise<void> {
  const res = await apiFetch("/items/export.csv", { accessToken })
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  try {
    const a = document.createElement("a")
    a.href = url
    a.download = "items.csv"
    document.body.appendChild(a)
    a.click()
    a.remove()
  } finally {
    // Defer revoke slightly so the browser can start the download
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

export async function importItemsCsv(
  file: File,
  accessToken: string | null,
): Promise<BulkImportSummary> {
  const form = new FormData()
  form.append("file", file)
  const res = await apiFetch("/items/bulk-import", {
    method: "POST",
    body: form,
    accessToken,
  })
  return (await res.json()) as BulkImportSummary
}
