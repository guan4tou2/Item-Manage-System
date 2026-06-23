import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type ItemLabel =
  paths["/api/items/{item_id}/label"]["get"]["responses"]["200"]["content"]["application/json"]

export interface ItemLabelBundle {
  itemId: string
  label: ItemLabel
  qrBlob: Blob
}

export interface BulkItemLabelBundles {
  items: ItemLabelBundle[]
  skippedCount: number
}

export async function getItemLabel(
  itemId: string,
  accessToken: string | null,
): Promise<ItemLabel> {
  const res = await apiFetch(`/items/${itemId}/label`, { accessToken })
  return (await res.json()) as ItemLabel
}

/** Fetch the QR PNG as a Blob; caller is responsible for object-URL lifetime. */
export async function getItemQrBlob(
  itemId: string,
  accessToken: string | null,
): Promise<Blob> {
  const res = await apiFetch(`/items/${itemId}/qr.png`, { accessToken })
  return await res.blob()
}

export async function getItemLabelBundle(
  itemId: string,
  accessToken: string | null,
): Promise<ItemLabelBundle> {
  const [label, qrBlob] = await Promise.all([
    getItemLabel(itemId, accessToken),
    getItemQrBlob(itemId, accessToken),
  ])
  return { itemId, label, qrBlob }
}

export async function getBulkItemLabelBundles(
  itemIds: string[],
  accessToken: string | null,
): Promise<BulkItemLabelBundles> {
  const uniqueIds = Array.from(new Set(itemIds.filter(Boolean)))
  const settled = await Promise.allSettled(
    uniqueIds.map((itemId) => getItemLabelBundle(itemId, accessToken)),
  )
  const items = settled.flatMap((result) =>
    result.status === "fulfilled" ? [result.value] : [],
  )
  return {
    items,
    skippedCount: settled.length - items.length,
  }
}
