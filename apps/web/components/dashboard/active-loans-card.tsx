"use client"

import Link from "next/link"

import type { ActiveLoan } from "@/lib/api/stats"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  loans: ActiveLoan[]
  loading?: boolean
}

function formatDate(iso: string | null): string {
  if (!iso) return "—"
  return iso.slice(0, 10)
}

export function ActiveLoansCard({ loans, loading }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">活躍借出</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">載入中…</p>
        ) : loans.length === 0 ? (
          <p className="text-sm text-muted-foreground">目前沒有未歸還的借出</p>
        ) : (
          <ul className="divide-y">
            {loans.map((loan) => (
              <li
                key={loan.loan_id}
                className="flex items-center justify-between gap-2 py-2"
              >
                <div className="min-w-0">
                  <Link
                    href={`/items/${loan.item_id}` as never}
                    className="block truncate hover:underline"
                  >
                    {loan.item_name}
                  </Link>
                  <div className="truncate text-xs text-muted-foreground">
                    借給 {loan.borrower_label ?? "—"} · 預計 {formatDate(loan.expected_return)}
                  </div>
                </div>
                {loan.is_overdue ? (
                  <span className="flex-shrink-0 rounded bg-destructive/10 px-1.5 py-0.5 text-xs text-destructive">
                    已逾期
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
