"use client"

import { useTranslations } from "next-intl"

import { SettingsPageShell } from "@/components/settings/settings-page-shell"
import { ReportsPanel } from "@/components/settings/reports-panel"

export default function SettingsReportsPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.reports.title")}
      description={t("settings.index.pages.reports.description")}
    >
      <ReportsPanel />
    </SettingsPageShell>
  )
}
