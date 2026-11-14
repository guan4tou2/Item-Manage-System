"use client"

import { useLocale, useTranslations } from "next-intl"
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

import { EmptyChart } from "@/components/stats/empty-chart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { CategoryValueBucket } from "@/lib/api/stats"
import { formatCurrency } from "@/lib/format/currency"

const PALETTE = [
  "#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#475569",
]

export interface CategoryValuePoint {
  name: string
  value: number
  count: number
}

export function toCategoryValueData(
  buckets: CategoryValueBucket[],
  uncategorized: string,
): CategoryValuePoint[] {
  return buckets
    .filter((b) => Number(b.value) > 0)
    .map((b) => ({
      name: b.name ?? uncategorized,
      value: Number(b.value),
      count: b.count,
    }))
}

interface Props {
  buckets: CategoryValueBucket[]
  currency: string
  loading?: boolean
}

export function ValueCategoryChart({ buckets, currency, loading }: Props) {
  const t = useTranslations()
  const locale = useLocale()
  const data = toCategoryValueData(buckets, t("stats.byCategory.uncategorized"))
  const empty = !loading && data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.value.byCategory")}</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                {data.map((entry, i) => (
                  <Cell key={entry.name} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value, _name, item) => {
                  const count =
                    (item?.payload as { count?: number } | undefined)?.count ?? 0
                  return t("stats.value.tooltip", {
                    amount: formatCurrency(Number(value), currency, locale),
                    count,
                  })
                }}
              />
              <Legend iconType="circle" />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
