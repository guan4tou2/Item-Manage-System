"use client"
import { useLocale, useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"

import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { CURRENCIES, formatCurrency, type Currency } from "@/lib/format/currency"
import { usePreferences, useUpdatePreferences } from "@/lib/preferences/use-preferences"

export function PreferencesForm() {
  const t = useTranslations()
  const locale = useLocale()
  const prefs = usePreferences()
  const update = useUpdatePreferences()
  const [aiSharing, setAiSharing] = useState<boolean | null>(null)

  const onThemeChange = async (theme: string) => {
    await update.mutateAsync({ theme: theme as "system" | "light" | "dark" })
    toast.success(t("settings.preferences.saved"))
  }
  const onLangChange = async (language: string) => {
    await update.mutateAsync({ language: language as "zh-TW" | "en" })
    toast.success(t("settings.preferences.saved"))
  }
  const onCurrencyChange = async (currency: string) => {
    await update.mutateAsync({ currency: currency as Currency })
    toast.success(t("settings.preferences.saved"))
  }
  const onAiSharingChange = async (enabled: boolean) => {
    setAiSharing(enabled)
    try {
      await update.mutateAsync({ ai_data_sharing_enabled: enabled })
      toast.success(
        enabled ? t("settings.preferences.aiSharingOn") : t("settings.preferences.aiSharingOff"),
      )
    } catch {
      // 失敗回滾為伺服器值（下一次 render 由 prefs 提供）
      setAiSharing(null)
      toast.error(t("settings.preferences.saveFailed"))
    }
  }

  const currency: string = prefs.data?.currency ?? "TWD"
  const aiSharingEnabled = aiSharing ?? prefs.data?.ai_data_sharing_enabled ?? false

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
      <div className="space-y-2">
        <Label>{t("settings.preferences.currency")}</Label>
        <Select value={currency} onValueChange={onCurrencyChange}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {CURRENCIES.map((code) => (
              <SelectItem key={code} value={code}>
                {t(`currency.${code}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-sm text-muted-foreground">
          {t("settings.preferences.currencyHint")}
        </p>
        <p className="text-sm text-muted-foreground" data-testid="currency-preview">
          {formatCurrency(1200, currency, locale)}
        </p>
      </div>
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <Label htmlFor="ai-data-sharing">{t("settings.preferences.aiSharing")}</Label>
            <p className="text-sm text-muted-foreground">
              {t("settings.preferences.aiSharingHint")}
            </p>
          </div>
          <Switch
            id="ai-data-sharing"
            checked={aiSharingEnabled}
            onCheckedChange={(checked) => void onAiSharingChange(checked)}
          />
        </div>
      </div>
    </div>
  )
}
