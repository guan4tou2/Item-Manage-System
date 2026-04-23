"use client"

import { useTranslations } from "next-intl"

import { AdminUsersPanel } from "@/components/settings/admin-users-panel"
import { ApiTokensPanel } from "@/components/settings/api-tokens-panel"
import { AuditLogPanel } from "@/components/settings/audit-log-panel"
import { BootstrapAdminButton } from "@/components/settings/bootstrap-admin-button"
import { PasswordForm } from "@/components/settings/password-form"
import { PreferencesForm } from "@/components/settings/preferences-form"
import { ProfileForm } from "@/components/settings/profile-form"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useMe } from "@/lib/hooks/use-profile"

export default function SettingsPage() {
  const t = useTranslations()
  const me = useMe()
  const isAdmin = me.data?.is_admin === true

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("settings.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("settings.title")}</h1>

      <BootstrapAdminButton />

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">{t("settings.tabs.profile")}</TabsTrigger>
          <TabsTrigger value="password">{t("settings.tabs.password")}</TabsTrigger>
          <TabsTrigger value="preferences">{t("settings.tabs.preferences")}</TabsTrigger>
          <TabsTrigger value="tokens">API Tokens</TabsTrigger>
          {isAdmin ? <TabsTrigger value="admin">{t("settings.tabs.admin")}</TabsTrigger> : null}
          {isAdmin ? <TabsTrigger value="audit">稽核日誌</TabsTrigger> : null}
        </TabsList>
        <TabsContent value="profile"><ProfileForm /></TabsContent>
        <TabsContent value="password"><PasswordForm /></TabsContent>
        <TabsContent value="preferences"><PreferencesForm /></TabsContent>
        <TabsContent value="tokens"><ApiTokensPanel /></TabsContent>
        {isAdmin ? (
          <TabsContent value="admin"><AdminUsersPanel /></TabsContent>
        ) : null}
        {isAdmin ? (
          <TabsContent value="audit"><AuditLogPanel /></TabsContent>
        ) : null}
      </Tabs>
    </section>
  )
}
