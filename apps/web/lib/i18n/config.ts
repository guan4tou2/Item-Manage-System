export const locales = ["zh-TW", "en"] as const
export type Locale = (typeof locales)[number]
export const defaultLocale: Locale = "zh-TW"

export function isLocale(value: string | undefined | null): value is Locale {
  return value === "zh-TW" || value === "en"
}

/** Parse any input (cookie or Accept-Language header) into a valid locale; fall back on failure. */
export function normalizeLocale(value: string | undefined | null): Locale {
  if (!value) return defaultLocale
  if (isLocale(value)) return value
  // Accept-Language may look like "en-US,en;q=0.9"
  const primary = value.split(",")[0]?.trim().toLowerCase() ?? ""
  if (primary.startsWith("zh")) return "zh-TW"
  if (primary.startsWith("en")) return "en"
  return defaultLocale
}
