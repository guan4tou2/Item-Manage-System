"use client"

import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"

export function DevThemeToggle() {
  const { theme, setTheme } = useTheme()
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
