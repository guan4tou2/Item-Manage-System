"use client"

import { useTranslations } from "next-intl"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyChart } from "@/components/stats/empty-chart"
import type { LocationBucket } from "@/lib/api/stats"

interface Props {
  buckets: LocationBucket[]
  loading?: boolean
}

export function LocationChart({ buckets, loading }: Props) {
  const t = useTranslations()
  const data = buckets.map((b) => ({
    name: b.label ?? t("stats.byLocation.unplaced"),
    count: b.count,
  }))
  const empty = !loading && data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.byLocation.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
