"use client"

import { useTranslations } from "next-intl"

import { CsvPanel } from "@/components/settings/csv-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsDataPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.data.title")}
      description={t("settings.index.pages.data.description")}
    >
      <CsvPanel />
    </SettingsPageShell>
  )
}
