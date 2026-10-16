"use client"

import { useTranslations } from "next-intl"

import { AdminOnly } from "@/components/settings/admin-only"
import { AdminUsersPanel } from "@/components/settings/admin-users-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsMembersPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.members.title")}
      description={t("settings.index.pages.members.description")}
    >
      <AdminOnly>
        <AdminUsersPanel />
      </AdminOnly>
    </SettingsPageShell>
  )
}
