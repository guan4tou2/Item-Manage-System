"use client"

import { useCallback } from "react"
import { useRouter } from "next/navigation"
import { useLocale as useNextIntlLocale } from "next-intl"

import { useAccessToken } from "@/lib/auth/use-auth"
import { useUpdatePreferences } from "@/lib/preferences/use-preferences"

import { writeLocaleCookie } from "./cookie"

import type { Locale } from "@/lib/i18n/config"

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
