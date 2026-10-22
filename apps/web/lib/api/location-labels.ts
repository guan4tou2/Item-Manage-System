import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type LocationLabel =
  paths["/api/locations/{location_id}/label"]["get"]["responses"]["200"]["content"]["application/json"]

export interface LocationLabelBundle {
  locationId: number
  label: LocationLabel
  qrBlob: Blob
}

export interface BulkLocationLabelBundles {
  labels: LocationLabelBundle[]
  skippedCount: number
}

export async function getLocationLabel(
  locationId: number,
  accessToken: string | null,
): Promise<LocationLabel> {
  const res = await apiFetch(`/locations/${locationId}/label`, { accessToken })
  return (await res.json()) as LocationLabel
}

/** Fetch the QR PNG as a Blob; caller is responsible for object-URL lifetime. */
export async function getLocationQrBlob(
  locationId: number,
  accessToken: string | null,
): Promise<Blob> {
  const res = await apiFetch(`/locations/${locationId}/qr.png`, { accessToken })
  return await res.blob()
}

export async function getLocationLabelBundle(
  locationId: number,
  accessToken: string | null,
): Promise<LocationLabelBundle> {
  const [label, qrBlob] = await Promise.all([
    getLocationLabel(locationId, accessToken),
    getLocationQrBlob(locationId, accessToken),
  ])
  return { locationId, label, qrBlob }
}

/** 批次取得多個位置標籤；失敗者略過（回傳 skippedCount）。 */
export async function getBulkLocationLabelBundles(
  locationIds: number[],
  accessToken: string | null,
): Promise<BulkLocationLabelBundles> {
  const unique = Array.from(new Set(locationIds.filter((id) => Number.isFinite(id))))
  const settled = await Promise.allSettled(
    unique.map((id) => getLocationLabelBundle(id, accessToken)),
  )
  const labels = settled.flatMap((result) =>
    result.status === "fulfilled" ? [result.value] : [],
  )
  return { labels, skippedCount: settled.length - labels.length }
}
