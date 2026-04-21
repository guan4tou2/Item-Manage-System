"use client"

import { Button } from "@/components/ui/button"
import { useThemePreference } from "@/lib/theme/use-theme"

export function DevThemeToggle() {
  const { theme, setTheme } = useThemePreference()
  const next = theme === "dark" ? "light" : "dark"
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => setTheme(next)}
      aria-label={`切換到 ${next === "dark" ? "深色" : "淺色"}模式`}
    >
      切換 {next === "dark" ? "深色" : "淺色"}
    </Button>
  )
}
