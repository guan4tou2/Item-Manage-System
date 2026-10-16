"use client"

import { useTranslations } from "next-intl"

import { RemindersPanel } from "@/components/settings/reminders-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsRemindersPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.reminders.title")}
      description={t("settings.index.pages.reminders.description")}
    >
      <RemindersPanel />
    </SettingsPageShell>
  )
}
