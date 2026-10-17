/**
 * 金額格式（roadmap §5.6，Phase 27 建立）。
 *
 * - `Intl.NumberFormat(locale, { style: "currency", currency })` 為底
 * - TWD 於 zh-TW／en 一律顯示 `NT$` 前綴（CLDR 對 zh-TW 會給 `$`，故以
 *   `formatToParts` 將 currency part 換為固定符號表）
 * - 小數位：JPY 一律 0 位；整數金額 0 位；有小數 2 位
 * - null／空字串／非數字 → `—`
 */
export const CURRENCIES = ["TWD", "USD", "EUR", "JPY", "CNY", "HKD"] as const

export type Currency = (typeof CURRENCIES)[number]

export const CURRENCY_SYMBOLS: Record<Currency, string> = {
  TWD: "NT$",
  USD: "US$",
  EUR: "€",
  JPY: "¥",
  CNY: "CN¥",
  HKD: "HK$",
}

const EM_DASH = "—"

function fractionDigits(amount: number, currency: string): number {
  if (currency === "JPY") return 0
  return Number.isInteger(amount) ? 0 : 2
}

export function formatCurrency(
  value: string | number | null | undefined,
  currency: string,
  locale: string,
): string {
  if (value === null || value === undefined || value === "") return EM_DASH
  const amount = typeof value === "number" ? value : Number(value)
  if (!Number.isFinite(amount)) return EM_DASH

  const digits = fractionDigits(amount, currency)
  try {
    const formatter = new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    })
    const symbol = CURRENCY_SYMBOLS[currency as Currency]
    if (!symbol) return formatter.format(amount)
    return formatter
      .formatToParts(amount)
      .map((part) => (part.type === "currency" ? symbol : part.value))
      .join("")
  } catch {
    // 未知／無效的幣別代碼：退回純數字顯示（永不拋錯）
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(amount)
  }
}
