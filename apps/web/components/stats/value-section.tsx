"use client"

import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useStatsValue } from "@/lib/hooks/use-stats"

import { ValueCategoryChart } from "./value-category-chart"
import { ValueLocationChart } from "./value-location-chart"
import { ValueSummaryCard } from "./value-summary-card"

export function ValueSection() {
  const t = useTranslations()
  const value = useStatsValue()

  return (
    <section className="space-y-4" data-testid="value-section">
      <h2 className="text-lg font-semibold">{t("stats.value.sectionTitle")}</h2>
      {value.isError ? (
        <Card>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
            <p role="alert" className="text-sm text-destructive">
              {t("stats.value.error")}
            </p>
            <Button variant="outline" size="sm" onClick={() => void value.refetch()}>
              {t("stats.value.retry")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <ValueSummaryCard data={value.data} loading={value.isLoading} />
          <div className="grid gap-4 md:grid-cols-2">
            <ValueCategoryChart
              buckets={value.data?.by_category ?? []}
              currency={value.data?.currency ?? "TWD"}
              loading={value.isLoading}
            />
            <ValueLocationChart
              buckets={value.data?.by_location ?? []}
              currency={value.data?.currency ?? "TWD"}
              loading={value.isLoading}
            />
          </div>
        </>
      )}
    </section>
  )
}
