'use client'

import { useTranslations } from 'next-intl'

import { AdminUsersPanel } from '@/components/settings/admin-users-panel'
import { ApiTokensPanel } from '@/components/settings/api-tokens-panel'
import { AuditLogPanel } from '@/components/settings/audit-log-panel'
import { BootstrapAdminButton } from '@/components/settings/bootstrap-admin-button'
import { CustomizationPanel } from '@/components/settings/customization-panel'
import { CsvPanel } from '@/components/settings/csv-panel'
import { NotificationChannelsPanel } from '@/components/settings/notification-channels-panel'
import { PasswordForm } from '@/components/settings/password-form'
import { PreferencesForm } from '@/components/settings/preferences-form'
import { ProfileForm } from '@/components/settings/profile-form'
import { WebhookPanel } from '@/components/settings/webhook-panel'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useMe } from '@/lib/hooks/use-profile'

export default function SettingsPage() {
  const t = useTranslations()
  const me = useMe()
  const isAdmin = me.data?.is_admin === true

  return (
    <section className="space-y-6 p-4 sm:p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t('settings.title')}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{t('settings.title')}</h1>
        <p className="text-muted-foreground max-w-3xl text-sm">{t('settings.subtitle')}</p>
      </div>

      <BootstrapAdminButton />

      <Tabs defaultValue="profile">
        <div className="-mx-4 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0">
          <TabsList className="w-max justify-start">
            <TabsTrigger value="profile">{t('settings.tabs.profile')}</TabsTrigger>
            <TabsTrigger value="password">{t('settings.tabs.password')}</TabsTrigger>
            <TabsTrigger value="preferences">{t('settings.tabs.preferences')}</TabsTrigger>
            <TabsTrigger value="tokens">{t('settings.tabs.tokens')}</TabsTrigger>
            <TabsTrigger value="customization">{t('settings.tabs.customization')}</TabsTrigger>
            <TabsTrigger value="channels">{t('settings.tabs.channels')}</TabsTrigger>
            <TabsTrigger value="webhooks">{t('settings.tabs.webhooks')}</TabsTrigger>
            <TabsTrigger value="data">{t('settings.tabs.data')}</TabsTrigger>
            {isAdmin ? <TabsTrigger value="admin">{t('settings.tabs.admin')}</TabsTrigger> : null}
            {isAdmin ? <TabsTrigger value="audit">{t('settings.tabs.audit')}</TabsTrigger> : null}
          </TabsList>
        </div>
        <TabsContent value="profile" className="mt-5">
          <ProfileForm />
        </TabsContent>
        <TabsContent value="password" className="mt-5">
          <PasswordForm />
        </TabsContent>
        <TabsContent value="preferences" className="mt-5">
          <PreferencesForm />
        </TabsContent>
        <TabsContent value="tokens" className="mt-5">
          <ApiTokensPanel />
        </TabsContent>
        <TabsContent value="customization" className="mt-5">
          <CustomizationPanel />
        </TabsContent>
        <TabsContent value="channels" className="mt-5">
          <NotificationChannelsPanel />
        </TabsContent>
        <TabsContent value="webhooks" className="mt-5">
          <WebhookPanel />
        </TabsContent>
        <TabsContent value="data" className="mt-5">
          <CsvPanel />
        </TabsContent>
        {isAdmin ? (
          <TabsContent value="admin" className="mt-5">
            <AdminUsersPanel />
          </TabsContent>
        ) : null}
        {isAdmin ? (
          <TabsContent value="audit" className="mt-5">
            <AuditLogPanel />
          </TabsContent>
        ) : null}
      </Tabs>
    </section>
  )
}
