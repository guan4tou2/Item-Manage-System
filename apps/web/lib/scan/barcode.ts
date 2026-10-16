/**
 * 掃描頁／表單共用的條碼工具（與 API `barcode_service.canonicalize` 同規則）。
 * API 端仍為權威；此處僅用於流程分流與 UI 顯示。
 */

const DIGITS_RE = /^\d{8,14}$/
const ISBN10_RE = /^\d{9}[\dXx]$/

/** 去空白／連字號／底線；數字（8–14 位）或 ISBN-10 收斂 canonical，其餘保留 trim 原樣。 */
export function canonicalizeBarcode(raw: string | null | undefined): string {
  if (!raw) return ""
  const trimmed = raw.trim()
  const cleaned = trimmed.replace(/[\s\-_]+/g, "")
  if (DIGITS_RE.test(cleaned) || ISBN10_RE.test(cleaned)) {
    return cleaned.toUpperCase()
  }
  return trimmed
}

/** 掃到的 payload 是否為條碼候選（值得打 lookup API）。 */
export function isBarcodeLike(raw: string | null | undefined): boolean {
  const canonical = canonicalizeBarcode(raw)
  return DIGITS_RE.test(canonical) || ISBN10_RE.test(canonical)
}
