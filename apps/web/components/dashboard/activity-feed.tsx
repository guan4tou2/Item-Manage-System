"use client"

import Link from "next/link"

import type { ActivityEntry } from "@/lib/api/stats"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  entries: ActivityEntry[]
  loading?: boolean
}

const KIND_LABEL: Record<string, string> = {
  quantity: "數量",
  loan_out: "借出",
  loan_return: "歸還",
  item_version: "快照",
}

function formatWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

export function ActivityFeed({ entries, loading }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">最近活動</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">載入中…</p>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">沒有最近活動</p>
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
