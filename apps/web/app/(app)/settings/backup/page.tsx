"use client"

import { useTranslations } from "next-intl"

import { BackupPanel } from "@/components/settings/backup-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsBackupPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.backup.title")}
      description={t("settings.index.pages.backup.description")}
    >
      <BackupPanel />
    </SettingsPageShell>
  )
}
