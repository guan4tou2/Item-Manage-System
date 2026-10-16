"use client"

import { useTranslations } from "next-intl"

import { NotificationPreferencesPanel } from "@/components/settings/notification-preferences-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsNotificationsPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.notifications.title")}
      description={t("settings.index.pages.notifications.description")}
    >
      <NotificationPreferencesPanel />
    </SettingsPageShell>
  )
}
