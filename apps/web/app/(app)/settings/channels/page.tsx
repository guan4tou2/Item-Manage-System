"use client"

import { useTranslations } from "next-intl"

import { NotificationChannelsPanel } from "@/components/settings/notification-channels-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsChannelsPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.channels.title")}
      description={t("settings.index.pages.channels.description")}
    >
      <NotificationChannelsPanel />
    </SettingsPageShell>
  )
}
