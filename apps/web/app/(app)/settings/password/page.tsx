"use client"

import { useTranslations } from "next-intl"

import { PasswordForm } from "@/components/settings/password-form"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsPasswordPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.password.title")}
      description={t("settings.index.pages.password.description")}
    >
      <PasswordForm />
    </SettingsPageShell>
  )
}
