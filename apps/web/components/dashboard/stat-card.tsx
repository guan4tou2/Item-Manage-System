import type { ReactNode } from "react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

interface Props {
  label: string
  value?: number
  icon?: ReactNode
  loading?: boolean
}

export function StatCard({ label, value, icon, loading }: Props) {
  return (
    <Card role="group" aria-label={label}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        {icon ? <span className="text-muted-foreground">{icon}</span> : null}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <div className="text-3xl font-semibold tabular-nums">{value ?? 0}</div>
        )}
      </CardContent>
    </Card>
  )
}
