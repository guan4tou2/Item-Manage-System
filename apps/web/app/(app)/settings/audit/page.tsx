"use client"

import { useTranslations } from "next-intl"

import { AdminOnly } from "@/components/settings/admin-only"
import { AuditLogPanel } from "@/components/settings/audit-log-panel"
import { SettingsPageShell } from "@/components/settings/settings-page-shell"

export default function SettingsAuditPage() {
  const t = useTranslations()
  return (
    <SettingsPageShell
      title={t("settings.index.pages.audit.title")}
      description={t("settings.index.pages.audit.description")}
    >
      <AdminOnly>
        <AuditLogPanel />
      </AdminOnly>
    </SettingsPageShell>
  )
}
