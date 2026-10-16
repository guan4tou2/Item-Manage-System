import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type BarcodeLookup =
  paths["/api/barcodes/{code}"]["get"]["responses"]["200"]["content"]["application/json"]
export type BarcodeLocalMatch = BarcodeLookup["local_matches"][number]
export type BarcodeExternal = NonNullable<BarcodeLookup["external"]>
export type BarcodeExternalStatus = BarcodeLookup["external_status"]

/** 內查＋外查（API 端處理快取與 fail-soft；此處僅轉發）。 */
export async function lookupBarcode(
  code: string,
  accessToken: string | null,
): Promise<BarcodeLookup> {
  const res = await apiFetch(`/barcodes/${encodeURIComponent(code)}`, { accessToken })
  return (await res.json()) as BarcodeLookup
}
