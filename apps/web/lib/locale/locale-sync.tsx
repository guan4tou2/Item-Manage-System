"use client"

import { useRouter } from "next/navigation"
import { useLocale as useNextIntlLocale } from "next-intl"
import { useEffect, useRef } from "react"

import { useAccessToken } from "@/lib/auth/use-auth"
import { isLocale } from "@/lib/i18n/config"
import { usePreferences } from "@/lib/preferences/use-preferences"

import { writeLocaleCookie } from "./cookie"

export function LocaleSync() {
  const token = useAccessToken()
  const { data, isSuccess } = usePreferences()
  const currentLocale = useNextIntlLocale()
  const router = useRouter()
  const syncedFor = useRef<string | null>(null)

  useEffect(() => {
    if (!token) {
      syncedFor.current = null
      return
    }
    if (!isSuccess || syncedFor.current === token) return
    const serverLang = data?.language
    if (serverLang && isLocale(serverLang) && serverLang !== currentLocale) {
      writeLocaleCookie(serverLang)
      router.refresh()
    }
    syncedFor.current = token
  }, [token, isSuccess, data, currentLocale, router])

  return null
}
