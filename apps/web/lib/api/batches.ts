import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type BatchRead = paths["/api/items/{item_id}/batches"]["get"]["responses"]["200"]["content"]["application/json"][number]
type BatchCreate = paths["/api/items/{item_id}/batches"]["post"]["requestBody"]["content"]["application/json"]
type BatchUpdate = paths["/api/items/{item_id}/batches/{batch_id}"]["patch"]["requestBody"]["content"]["application/json"]
type BatchConsume = paths["/api/items/{item_id}/batches/{batch_id}/consume"]["post"]["requestBody"]["content"]["application/json"]
type BatchConsumeResult = paths["/api/items/{item_id}/consume"]["post"]["responses"]["200"]["content"]["application/json"]
type BatchDisableResult = paths["/api/items/{item_id}/batches/disable"]["post"]["responses"]["200"]["content"]["application/json"]

export type { BatchRead, BatchCreate, BatchUpdate, BatchConsume, BatchConsumeResult, BatchDisableResult }

export async function listBatches(itemId: string, accessToken: string | null): Promise<BatchRead[]> {
  const res = await apiFetch(`/items/${itemId}/batches`, { accessToken })
  return (await res.json()) as BatchRead[]
}

export async function createBatch(
  itemId: string,
  body: BatchCreate,
  accessToken: string | null,
): Promise<BatchRead> {
  const res = await apiFetch(`/items/${itemId}/batches`, {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as BatchRead
}

export async function updateBatch(
  itemId: string,
  batchId: string,
  body: BatchUpdate,
  accessToken: string | null,
): Promise<BatchRead> {
  const res = await apiFetch(`/items/${itemId}/batches/${batchId}`, {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as BatchRead
}

export async function deleteBatch(
  itemId: string,
  batchId: string,
  accessToken: string | null,
): Promise<void> {
  await apiFetch(`/items/${itemId}/batches/${batchId}`, { method: "DELETE", accessToken })
}

export async function consumeBatch(
  itemId: string,
  batchId: string,
  body: BatchConsume,
  accessToken: string | null,
): Promise<BatchRead> {
  const res = await apiFetch(`/items/${itemId}/batches/${batchId}/consume`, {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as BatchRead
}

export async function consumeFefo(
  itemId: string,
  body: BatchConsume,
  accessToken: string | null,
): Promise<BatchConsumeResult> {
  const res = await apiFetch(`/items/${itemId}/consume`, {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as BatchConsumeResult
}

export async function disableBatches(
  itemId: string,
  accessToken: string | null,
): Promise<BatchDisableResult> {
  const res = await apiFetch(`/items/${itemId}/batches/disable`, {
    method: "POST", accessToken,
  })
  return (await res.json()) as BatchDisableResult
}
