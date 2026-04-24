import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type ItemLabel =
  paths["/api/items/{item_id}/label"]["get"]["responses"]["200"]["content"]["application/json"]

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
