"use client"

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyChart } from "@/components/stats/empty-chart"
import type { TrendPoint } from "@/lib/api/stats"

interface Props {
  points: TrendPoint[]
  loading?: boolean
}

export function TrendChart({ points, loading }: Props) {
  const data = points.map((p) => ({
    day: p.day.slice(5), // MM-DD
    count: p.count,
  }))
  const empty = !loading && (data.length === 0 || data.every((p) => p.count === 0))

  return (
    <Card>
      <CardHeader>
        <CardTitle>新增趨勢 (近 30 天)</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="day" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={30} />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#2563eb"
                fillOpacity={1}
                fill="url(#trendFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
