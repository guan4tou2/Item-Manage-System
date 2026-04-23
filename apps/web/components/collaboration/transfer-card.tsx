"use client"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAcceptTransfer, useCancelTransfer, useRejectTransfer } from "@/lib/hooks/use-transfers"
import type { Transfer } from "@/lib/api/transfers"

export function TransferCard({ row, currentUserId }: { row: Transfer; currentUserId: string }) {
  const t = useTranslations()
  const accept = useAcceptTransfer()
  const reject = useRejectTransfer()
  const cancel = useCancelTransfer()
  const isIncoming = row.to_user_id === currentUserId
  const peer = isIncoming ? row.from_username : row.to_username
  const isPending = row.status === "pending"

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <CardTitle className="text-base">{row.item_name}</CardTitle>
        <Badge variant={isPending ? "default" : "secondary"}>{t(`collab.transfers.status.${row.status}`)}</Badge>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        <p>{isIncoming ? `${peer} → 你` : `你 → ${peer}`}</p>
        {row.message ? <p className="mt-1">{row.message}</p> : null}
      </CardContent>
      {isPending ? (
        <CardFooter className="gap-2">
          {isIncoming ? (
            <>
              <Button size="sm" onClick={() => accept.mutate(row.id)} disabled={accept.isPending}>
                {t("collab.transfers.actions.accept")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => reject.mutate(row.id)} disabled={reject.isPending}>
                {t("collab.transfers.actions.reject")}
              </Button>
            </>
          ) : (
            <Button size="sm" variant="outline" onClick={() => cancel.mutate(row.id)} disabled={cancel.isPending}>
              {t("collab.transfers.actions.cancel")}
            </Button>
          )}
        </CardFooter>
      ) : null}
    </Card>
  )
}
