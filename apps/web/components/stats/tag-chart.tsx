"use client"

import { useTranslations } from "next-intl"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyChart } from "@/components/stats/empty-chart"
import type { TagBucket } from "@/lib/api/stats"

interface Props {
  buckets: TagBucket[]
  loading?: boolean
}

export function TagChart({ buckets, loading }: Props) {
  const t = useTranslations()
  const data = buckets.map((b) => ({ name: b.name, count: b.count }))
  const empty = !loading && data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.byTag.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(240, data.length * 28)}>
            <BarChart data={data} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#16a34a" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
