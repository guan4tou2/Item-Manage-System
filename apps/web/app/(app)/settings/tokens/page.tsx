"use client"

import { useTranslations } from "next-intl"

import { ApiTokensPanel } from "@/components/settings/api-tokens-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsTokensPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.tokens.title")}
      description={t("settings.index.pages.tokens.description")}
    >
      <ApiTokensPanel />
    </SettingsPageShell>
  )
}
