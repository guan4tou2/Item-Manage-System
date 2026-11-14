import type { ItemFormValues } from "@/components/items/item-form"
import type { ItemCreate, ItemUpdate } from "@/lib/api/items"
import { itemCostPayload } from "@/lib/items/cost"
import type { PendingItem } from "./storage"
import type { OfflineStep } from "./engine"

export function createBody(values: ItemFormValues): ItemCreate {
  return {
    name: values.name, description: values.description || undefined,
    barcode: values.barcode || undefined, cost: itemCostPayload(values.cost),
    category_id: values.category_id ?? undefined, location_id: values.location_id ?? undefined,
    quantity: values.quantity, notes: values.notes || undefined,
    image_id: values.image_id ?? undefined, tag_names: values.tag_names,
  }
}
export function updateBody(values: ItemFormValues, tracking: boolean): ItemUpdate {
  return {
    name: values.name, description: values.description || null, barcode: values.barcode || null,
    cost: itemCostPayload(values.cost), category_id: values.category_id, location_id: values.location_id,
    ...(tracking ? {} : { quantity: values.quantity }), notes: values.notes || null,
    image_id: values.image_id ?? null, tag_names: values.tag_names,
  }
}
export function buildSteps(row: PendingItem): OfflineStep[] {
  const kind = row.kind ?? "create"
  const path = kind === "create" ? "/items/{item_id}" : `/items/${encodeURIComponent(row.item_id!)}`
  const headers = row.base_updated_at ? { "If-Match": row.base_updated_at } : undefined
  if (kind === "delete") return [{ method: "DELETE", path, headers }]
  const steps: OfflineStep[] = kind === "create"
    ? [{ method: "POST", path: "/items", body: createBody(row.values), headers: { "Idempotency-Key": row.client_id } }]
    : [{ method: "PATCH", path, body: updateBody(row.values, row.trackBatches), headers }]
  if (kind === "create" && row.trackBatches) steps.push({ method: "POST", path: `${path}/batches`, body: {} })
  for (const field of row.customFields) {
    const value = row.values.custom_values[String(field.id)]
    steps.push(value === null || value === undefined || value === ""
      ? { method: "DELETE", path: `${path}/custom-values/${field.id}`, tolerate404: true }
      : { method: "POST", path: `${path}/custom-values`, body: { custom_field_id: field.id, value } })
  }
  return steps
}

/** Apply D7 only on enqueue, never when persisting replay results. */
export function mergePending(incoming: PendingItem, rows: PendingItem[]): PendingItem {
  if (!incoming.item_id || incoming.kind === "create") return incoming
  const previous = rows.find((row) => row.item_id === incoming.item_id && row.kind !== "create")
  if (!previous) return incoming
  if (previous.kind === "delete") return previous
  return { ...incoming, client_id: previous.client_id, created_at: previous.created_at, base_updated_at: previous.base_updated_at }
}
