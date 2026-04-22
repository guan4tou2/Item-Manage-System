"use client"

import { useCallback } from "react"
import { useRouter } from "next/navigation"
import { useLocale as useNextIntlLocale } from "next-intl"

import { useAccessToken } from "@/lib/auth/use-auth"
import { useUpdatePreferences } from "@/lib/preferences/use-preferences"

import type { Locale } from "@/lib/i18n/config"

const COOKIE_NAME = "ims_locale"
const MAX_AGE = 60 * 60 * 24 * 365 // 1 year

function writeLocaleCookie(locale: Locale): void {
  if (typeof document === "undefined") return
  document.cookie = `${COOKIE_NAME}=${locale}; Path=/; SameSite=Lax; Max-Age=${MAX_AGE}`
}

export function useLocale(): {
  locale: Locale
  setLocale: (next: Locale) => void
  isSyncing: boolean
} {
  const locale = useNextIntlLocale() as Locale
  const token = useAccessToken()
  const update = useUpdatePreferences()
  const router = useRouter()

  const setLocale = useCallback(
    (next: Locale) => {
      writeLocaleCookie(next)
      if (token) {
        update.mutate({ language: next })
      }
      router.refresh()
    },
    [token, update, router],
  )

  return { locale, setLocale, isSyncing: update.isPending }
}
