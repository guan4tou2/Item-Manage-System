/**
 * 位置深連結辨識（Phase 36）。
 *
 * 位置標籤的 QR 內容為 `{base}/items?location={id}`（位置 id 為 int），
 * 掃碼後導向該位置（含子孫）的物品清單。
 *
 * 與物品深連結（`/items/{uuid}`）不衝突：物品連結的 pathname 帶 uuid 且無 query。
 */

/** 從掃到的 payload 取出位置 id；非位置深連結 → `null`。 */
export function extractLocationIdFromPayload(payload: string): string | null {
  const trimmed = (payload ?? "").trim()
  if (!trimmed) return null

  let url: URL
  try {
    url = new URL(trimmed)
  } catch {
    return null
  }

  const raw = url.searchParams.get("location")
  if (!raw) return null
  if (!/^\d+$/.test(raw)) return null

  const id = Number(raw)
  if (!Number.isSafeInteger(id) || id <= 0) return null
  return String(id)
}

/** 位置深連結的物品清單路徑（含位置篩選；`location_scope` 預設含子孫）。 */
export function locationItemsPath(locationId: string): string {
  return `/items?location=${encodeURIComponent(locationId)}`
}
