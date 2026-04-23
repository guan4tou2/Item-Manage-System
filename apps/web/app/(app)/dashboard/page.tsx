"use client"

import { useTranslations } from "next-intl"

import { ActiveLoansCard } from "@/components/dashboard/active-loans-card"
import { ActivityFeed } from "@/components/dashboard/activity-feed"
import { LowStockCard } from "@/components/dashboard/low-stock-card"
import { QuickLinks } from "@/components/dashboard/quick-links"
import { RecentItemsCard } from "@/components/dashboard/recent-items-card"
import { StatCard } from "@/components/dashboard/stat-card"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import {
  useActiveLoans,
  useActivity,
  useLowStock,
  useOverview,
  useRecent,
} from "@/lib/hooks/use-stats"

export default function DashboardPage() {
  const t = useTranslations()
  const overview = useOverview()
  const recent = useRecent(5)
  const lowStock = useLowStock(5)
  const activeLoans = useActiveLoans(5)
  const activity = useActivity(10)

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

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard
          label="倉庫"
          value={overview.data?.total_warehouses}
          loading={overview.isLoading}
        />
        <StatCard
          label="低庫存"
          value={overview.data?.low_stock_items}
          loading={overview.isLoading}
          tone="warn"
        />
        <StatCard
          label="活躍借出"
          value={overview.data?.active_loans}
          loading={overview.isLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <LowStockCard items={lowStock.data ?? []} loading={lowStock.isLoading} />
        <ActiveLoansCard
          loans={activeLoans.data ?? []}
          loading={activeLoans.isLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <RecentItemsCard items={recent.data ?? []} />
        <ActivityFeed entries={activity.data ?? []} loading={activity.isLoading} />
      </div>

      <QuickLinks />
    </section>
  )
}
