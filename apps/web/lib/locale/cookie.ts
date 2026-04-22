import type { Locale } from "@/lib/i18n/config"

export const LOCALE_COOKIE_NAME = "ims_locale"
export const LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 // 1 year

export function writeLocaleCookie(locale: Locale): void {
  if (typeof document === "undefined") return
  document.cookie = `${LOCALE_COOKIE_NAME}=${locale}; Path=/; SameSite=Lax; Max-Age=${LOCALE_COOKIE_MAX_AGE}`
}
