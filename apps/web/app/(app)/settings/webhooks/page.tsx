"use client"

import { useTranslations } from "next-intl"

import { SettingsPageShell } from "@/components/settings/settings-page-shell"
import { WebhookPanel } from "@/components/settings/webhook-panel"

export default function SettingsWebhooksPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.webhooks.title")}
      description={t("settings.index.pages.webhooks.description")}
    >
      <WebhookPanel />
    </SettingsPageShell>
  )
}
