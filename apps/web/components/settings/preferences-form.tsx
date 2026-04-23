"use client"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { usePreferences, useUpdatePreferences } from "@/lib/preferences/use-preferences"

export function PreferencesForm() {
  const t = useTranslations()
  const prefs = usePreferences()
  const update = useUpdatePreferences()

  const onThemeChange = async (theme: string) => {
    await update.mutateAsync({ theme: theme as "system" | "light" | "dark" })
    toast.success(t("settings.preferences.saved"))
  }
  const onLangChange = async (language: string) => {
    await update.mutateAsync({ language: language as "zh-TW" | "en" })
    toast.success(t("settings.preferences.saved"))
  }

  return (
    <div className="max-w-md space-y-6">
      <div className="space-y-2">
        <Label>{t("settings.preferences.theme")}</Label>
        <Select value={prefs.data?.theme ?? "system"} onValueChange={onThemeChange}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="system">{t("theme.system")}</SelectItem>
            <SelectItem value="light">{t("theme.light")}</SelectItem>
            <SelectItem value="dark">{t("theme.dark")}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>{t("settings.preferences.language")}</Label>
        <Select value={prefs.data?.language ?? "zh-TW"} onValueChange={onLangChange}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="zh-TW">{t("locale.zh-TW")}</SelectItem>
            <SelectItem value="en">{t("locale.en")}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
