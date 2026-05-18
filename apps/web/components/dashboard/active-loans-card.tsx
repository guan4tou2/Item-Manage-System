"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

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
  const t = useTranslations()
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.activeLoans.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.activeLoans.loading")}</p>
        ) : loans.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.activeLoans.empty")}</p>
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
                    {t("dashboard.activeLoans.loanInfo", { borrower: loan.borrower_label ?? "—", date: formatDate(loan.expected_return) })}
                  </div>
                </div>
                {loan.is_overdue ? (
                  <span className="flex-shrink-0 rounded bg-destructive/10 px-1.5 py-0.5 text-xs text-destructive">
                    {t("dashboard.activeLoans.overdue")}
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
