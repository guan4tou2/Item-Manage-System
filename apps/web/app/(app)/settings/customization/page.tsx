"use client"

import { useTranslations } from "next-intl"

import { CustomizationPanel } from "@/components/settings/customization-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsCustomizationPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.customization.title")}
      description={t("settings.index.pages.customization.description")}
    >
      <CustomizationPanel />
    </SettingsPageShell>
  )
}
