"use client"

import { useTheme } from "next-themes"
import { useEffect, useRef } from "react"

import { usePreferences } from "@/lib/preferences/use-preferences"

export function ThemeSync() {
  const { data, isSuccess } = usePreferences()
  const { setTheme } = useTheme()
  const synced = useRef(false)

  useEffect(() => {
    if (!isSuccess || synced.current) return
    if (data?.theme) {
      setTheme(data.theme)
    }
    synced.current = true
  }, [isSuccess, data, setTheme])

  return null
}
