"use client"

import { useTranslations } from "next-intl"

import { QuickLinks } from "@/components/dashboard/quick-links"
import { RecentItemsCard } from "@/components/dashboard/recent-items-card"
import { StatCard } from "@/components/dashboard/stat-card"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { useOverview, useRecent } from "@/lib/hooks/use-stats"

export default function DashboardPage() {
  const t = useTranslations()
  const overview = useOverview()
  const recent = useRecent(5)

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.dashboard")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div>
        <h1 className="text-2xl font-semibold">{t("dashboard.title")}</h1>
      </div>

      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <StatCard
          label={t("dashboard.overview.items")}
          value={overview.data?.total_items}
          loading={overview.isLoading}
        />
        <StatCard
          label={t("dashboard.overview.quantity")}
          value={overview.data?.total_quantity}
          loading={overview.isLoading}
        />
        <StatCard
          label={t("dashboard.overview.categories")}
          value={overview.data?.total_categories}
          loading={overview.isLoading}
        />
        <StatCard
          label={t("dashboard.overview.locations")}
          value={overview.data?.total_locations}
          loading={overview.isLoading}
        />
      </div>

      <RecentItemsCard items={recent.data ?? []} />

      <QuickLinks />
    </section>
  )
}
