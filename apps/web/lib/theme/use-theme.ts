"use client"

import { useTheme as useNextTheme } from "next-themes"
import { useCallback } from "react"

import {
  useUpdatePreferences,
  usePreferences,
} from "@/lib/preferences/use-preferences"
import type { ThemePreference } from "@/lib/preferences/types"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useThemePreference() {
  const { theme, setTheme: setNextTheme } = useNextTheme()
  const token = useAccessToken()
  const update = useUpdatePreferences()

  const setTheme = useCallback(
    (next: ThemePreference) => {
      setNextTheme(next)
      if (token) {
        update.mutate({ theme: next })
      }
    },
    [setNextTheme, token, update],
  )

  return {
    theme: (theme ?? "system") as ThemePreference,
    setTheme,
    isSyncing: update.isPending,
  }
}

export { usePreferences }
