"use client"

import { useTranslations } from "next-intl"

import { CategoryChart } from "@/components/stats/category-chart"
import { LocationChart } from "@/components/stats/location-chart"
import { TagChart } from "@/components/stats/tag-chart"
import { TrendChart } from "@/components/stats/trend-chart"
import { WarehouseChart } from "@/components/stats/warehouse-chart"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  useByCategory,
  useByLocation,
  useByTag,
  useByWarehouse,
  useTrend,
} from "@/lib/hooks/use-stats"

export default function StatisticsPage() {
  const t = useTranslations()
  const cats = useByCategory()
  const locs = useByLocation()
  const tags = useByTag(10)
  const warehouses = useByWarehouse()
  const trend = useTrend(30)

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/dashboard">{t("nav.dashboard")}</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{t("stats.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <h1 className="text-2xl font-semibold">{t("stats.title")}</h1>

      <TrendChart points={trend.data ?? []} loading={trend.isLoading} />

      <div className="grid gap-4 md:grid-cols-2">
        <CategoryChart buckets={cats.data ?? []} loading={cats.isLoading} />
        <LocationChart buckets={locs.data ?? []} loading={locs.isLoading} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <WarehouseChart
          buckets={warehouses.data ?? []}
          loading={warehouses.isLoading}
        />
        <TagChart buckets={tags.data ?? []} loading={tags.isLoading} />
      </div>
    </section>
  )
}
