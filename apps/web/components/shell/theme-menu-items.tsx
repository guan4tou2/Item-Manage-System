"use client"

import { useTranslations } from "next-intl"

import {
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu"
import { useThemePreference } from "@/lib/theme/use-theme"

export function ThemeMenuItems() {
  const t = useTranslations()
  const { theme, setTheme, isSyncing } = useThemePreference()
  const current = theme ?? "system"

  return (
    <DropdownMenuRadioGroup
      value={current}
      onValueChange={(value) =>
        setTheme(value as "system" | "light" | "dark")
      }
    >
      <DropdownMenuRadioItem value="system" disabled={isSyncing}>
        {t("theme.system")}
      </DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="light" disabled={isSyncing}>
        {t("theme.light")}
      </DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="dark" disabled={isSyncing}>
        {t("theme.dark")}
      </DropdownMenuRadioItem>
    </DropdownMenuRadioGroup>
  )
}
