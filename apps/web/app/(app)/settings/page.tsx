"use client"

import { useTranslations } from "next-intl"

import { AdminUsersPanel } from "@/components/settings/admin-users-panel"
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
          {isAdmin ? <TabsTrigger value="admin">{t("settings.tabs.admin")}</TabsTrigger> : null}
        </TabsList>
        <TabsContent value="profile"><ProfileForm /></TabsContent>
        <TabsContent value="password"><PasswordForm /></TabsContent>
        <TabsContent value="preferences"><PreferencesForm /></TabsContent>
        {isAdmin ? (
          <TabsContent value="admin"><AdminUsersPanel /></TabsContent>
        ) : null}
      </Tabs>
    </section>
  )
}
