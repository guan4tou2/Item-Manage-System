"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import type { ActivityEntry } from "@/lib/api/stats"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  entries: ActivityEntry[]
  loading?: boolean
}

function formatWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

export function ActivityFeed({ entries, loading }: Props) {
  const t = useTranslations()
  const KIND_LABEL: Record<string, string> = {
    quantity: t("dashboard.activity.kindQuantity"),
    loan_out: t("dashboard.activity.kindLoanOut"),
    loan_return: t("dashboard.activity.kindLoanReturn"),
    item_version: t("dashboard.activity.kindSnapshot"),
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.activity.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.activity.loading")}</p>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.activity.empty")}</p>
        ) : (
          <ul className="divide-y">
            {entries.map((entry, idx) => (
              <li
                key={`${entry.kind}-${entry.at}-${idx}`}
                className="flex items-start gap-3 py-2"
              >
                <span className="mt-0.5 flex-shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                  {KIND_LABEL[entry.kind] ?? entry.kind}
                </span>
                <div className="min-w-0 flex-1">
                  {entry.item_id ? (
                    <Link
                      href={`/items/${entry.item_id}` as never}
                      className="block truncate hover:underline"
                    >
                      {entry.summary}
                    </Link>
                  ) : (
                    <span className="block truncate">{entry.summary}</span>
                  )}
                  <div className="text-xs text-muted-foreground">
                    {formatWhen(entry.at)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
