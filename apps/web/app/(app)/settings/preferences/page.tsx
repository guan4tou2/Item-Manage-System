"use client"

import { useTranslations } from "next-intl"

import { PreferencesForm } from "@/components/settings/preferences-form"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsPreferencesPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.preferences.title")}
      description={t("settings.index.pages.preferences.description")}
    >
      <PreferencesForm />
    </SettingsPageShell>
  )
}
