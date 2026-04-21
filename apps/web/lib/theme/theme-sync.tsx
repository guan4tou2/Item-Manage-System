"use client"

import { useTheme } from "next-themes"
import { useEffect, useRef } from "react"

import { useAccessToken } from "@/lib/auth/use-auth"
import { usePreferences } from "@/lib/preferences/use-preferences"

export function ThemeSync() {
  const token = useAccessToken()
  const { data, isSuccess } = usePreferences()
  const { setTheme } = useTheme()
  const syncedFor = useRef<string | null>(null)

  useEffect(() => {
    if (!token) {
      syncedFor.current = null
      return
    }
    if (!isSuccess || syncedFor.current === token) return
    if (data?.theme) {
      setTheme(data.theme)
    }
    syncedFor.current = token
  }, [token, isSuccess, data, setTheme])

  return null
}
