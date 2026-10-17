"use client"

import { useLocale, useTranslations } from "next-intl"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { EmptyChart } from "@/components/stats/empty-chart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { LocationValueBucket } from "@/lib/api/stats"
import { formatCurrency } from "@/lib/format/currency"

export interface LocationValuePoint {
  /** 軸標籤（長路徑截斷） */
  name: string
  /** Tooltip 顯示的完整路徑 */
  full: string
  value: number
}

export function truncateLabel(label: string, max = 24): string {
  return label.length > max ? `${label.slice(0, max - 1)}…` : label
}

export function toLocationValueData(
  buckets: LocationValueBucket[],
  unplaced: string,
): LocationValuePoint[] {
  return buckets
    .filter((b) => Number(b.value) > 0)
    .map((b) => {
      const full = b.label ?? unplaced
      return { name: truncateLabel(full), full, value: Number(b.value) }
    })
}

interface Props {
  buckets: LocationValueBucket[]
  currency: string
  loading?: boolean
}

export function ValueLocationChart({ buckets, currency, loading }: Props) {
  const t = useTranslations()
  const locale = useLocale()
  const data = toLocationValueData(buckets, t("stats.value.noLocation"))
  const empty = !loading && data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.value.byLocation")}</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(240, data.length * 28)}>
            <BarChart data={data} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                tickFormatter={(value) => formatCurrency(Number(value), currency, locale)}
              />
              <YAxis type="category" dataKey="name" width={140} />
              <Tooltip
                formatter={(value) => formatCurrency(Number(value), currency, locale)}
                labelFormatter={(_label, payload) =>
                  (payload?.[0]?.payload as LocationValuePoint | undefined)?.full ?? ""
                }
              />
              <Bar dataKey="value" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
