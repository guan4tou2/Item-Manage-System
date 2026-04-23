"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { KindBadge } from "@/components/lists/kind-badge"
import type { ListKind, ListSummary } from "@/lib/api/lists"

interface Props {
  row: ListSummary
}

export function ListCard({ row }: Props) {
  const t = useTranslations()
  const kind = row.kind as ListKind

  return (
    <Link href={`/lists/${row.id}` as never} className="block no-underline">
      <Card className="transition-shadow hover:shadow-md">
        <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
          <CardTitle className="text-base">{row.title}</CardTitle>
          <KindBadge kind={kind} />
        </CardHeader>
        <CardContent className="space-y-1 text-sm text-muted-foreground">
          {kind === "travel" && row.start_date && row.end_date ? (
            <p>
              {t("lists.detail.dateRange", { start: row.start_date, end: row.end_date })}
            </p>
          ) : null}
          {kind === "shopping" && row.budget !== null ? (
            <p>{t("lists.detail.budget", { amount: row.budget })}</p>
          ) : null}
          <p>
            {t("lists.detail.entryCount", { count: row.entry_count, done: row.done_count })}
          </p>
        </CardContent>
      </Card>
    </Link>
  )
}
