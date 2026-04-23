"use client"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { NewLoanDialog } from "@/components/collaboration/new-loan-dialog"
import { useDeleteLoan, useLoans, useReturnLoan } from "@/lib/hooks/use-loans"

export function LoanCard({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const { data } = useLoans(itemId)
  const ret = useReturnLoan(itemId)
  const del = useDeleteLoan(itemId)
  const all = data ?? []
  const active = all.find((l) => l.returned_at === null) ?? null
  const history = all.filter((l) => l.returned_at !== null)

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">{t("collab.loan.card.title")}</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm">
        {active ? (
          <div>
            <p className="font-medium">
              {active.borrower_username ? t("collab.loan.card.borrowerUser", { username: active.borrower_username }) : active.borrower_label}
            </p>
            {active.expected_return ? <p className="text-muted-foreground">{t("collab.loan.card.expectedReturn", { date: active.expected_return })}</p> : null}
            {active.notes ? <p className="text-muted-foreground">{active.notes}</p> : null}
          </div>
        ) : (
          <p className="text-muted-foreground">—</p>
        )}
        {history.length > 0 ? (
          <details>
            <summary className="cursor-pointer text-muted-foreground">{t("collab.loan.card.history")} ({history.length})</summary>
            <ul className="mt-2 space-y-1">
              {history.map((l) => (
                <li key={l.id} className="flex items-center justify-between">
                  <span>{l.borrower_username ?? l.borrower_label}</span>
                  <Button size="sm" variant="ghost" onClick={() => del.mutate(l.id)}>{t("collab.loan.actions.delete")}</Button>
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </CardContent>
      <CardFooter className="gap-2">
        {active ? (
          <Button size="sm" onClick={() => ret.mutate(active.id)} disabled={ret.isPending}>
            {t("collab.loan.actions.return")}
          </Button>
        ) : (
          <NewLoanDialog itemId={itemId} />
        )}
      </CardFooter>
    </Card>
  )
}
