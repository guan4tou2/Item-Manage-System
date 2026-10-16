"use client"

import { useTranslations } from "next-intl"

import { ProfileForm } from "@/components/settings/profile-form"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsProfilePage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.profile.title")}
      description={t("settings.index.pages.profile.description")}
    >
      <ProfileForm />
    </SettingsPageShell>
  )
}
