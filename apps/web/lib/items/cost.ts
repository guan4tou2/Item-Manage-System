/**
 * 表單成本值 → API payload（Phase 27）。
 *
 * 空白（含純空白）→ `null`（建立＝不設；更新＝清空）。
 * 其餘 trim 後原樣送出（伺服器以 Decimal ge=0 / 2dp 為權威）。
 */
export function itemCostPayload(raw: string | null | undefined): string | null {
  const text = (raw ?? "").trim()
  return text === "" ? null : text
}
