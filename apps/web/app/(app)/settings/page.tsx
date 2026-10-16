"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { ChevronRight } from "lucide-react"

import { BootstrapAdminButton } from "@/components/settings/bootstrap-admin-button"
import { SETTINGS_GROUPS } from "@/components/settings/settings-nav"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useMe } from "@/lib/hooks/use-profile"

export default function SettingsPage() {
  const t = useTranslations()
  const me = useMe()
  const isAdmin = me.data?.is_admin === true
  const groups = SETTINGS_GROUPS.filter((group) => !group.pages.every((p) => p.adminOnly) || isAdmin)

  return (
    <section className="space-y-6 p-4 sm:p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("settings.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">{t("settings.title")}</h1>
        <p className="text-muted-foreground max-w-3xl text-sm">{t("settings.subtitle")}</p>
      </div>

      <BootstrapAdminButton />

      {me.isError ? (
        <Card className="border-dashed">
          <CardContent className="space-y-3 pt-6">
            <p className="text-sm text-muted-foreground">{t("settings.index.loadError")}</p>
            <Button size="sm" variant="outline" onClick={() => me.refetch()}>
              {t("settings.index.retry")}
            </Button>
          </CardContent>
        </Card>
      ) : me.isLoading ? (
        <div
          aria-busy="true"
          aria-label={t("settings.index.loading")}
          className="grid gap-4 md:grid-cols-2"
        >
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-44 animate-pulse rounded-lg border bg-muted/40" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {groups.map((group) => (
            <Card key={group.id}>
              <CardHeader>
                <CardTitle className="text-lg">
                  {t(`settings.index.groups.${group.id}.title`)}
                </CardTitle>
                <CardDescription>
                  {t(`settings.index.groups.${group.id}.description`)}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1">
                  {group.pages.map((page) => (
                    <li key={page.id}>
                      <Link
                        href={page.href}
                        className="group -mx-2 flex items-center gap-3 rounded-md px-2 py-2 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block text-sm font-medium">
                            {t(`settings.index.pages.${page.id}.title`)}
                          </span>
                          <span className="block text-xs text-muted-foreground">
                            {t(`settings.index.pages.${page.id}.description`)}
                          </span>
                        </span>
                        <ChevronRight
                          aria-hidden="true"
                          className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5"
                        />
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  )
}
