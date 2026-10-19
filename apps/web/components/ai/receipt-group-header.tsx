"use client"

import { useLocale, useTranslations } from "next-intl"
import { AlertTriangle, CheckCircle2 } from "lucide-react"

import type { ReceiptSnapshot } from "@/lib/api/ai-receipts"
import { receiptTotalsMatch } from "@/lib/ai/receipts"
import { formatCurrency } from "@/lib/format/currency"
import { cn } from "@/lib/utils"

interface Props {
  snapshot: ReceiptSnapshot | null
  itemCount: number
}

/** 收據對帳狀態：相符／差額警示／未標示總額。 */
export function ReceiptGroupHeader({ snapshot, itemCount }: Props) {
  const t = useTranslations()
  const locale = useLocale()
  const currency = snapshot?.currency ?? "TWD"

  const hasTotal = snapshot?.total !== null && snapshot?.total !== undefined
  const matches =
    hasTotal && receiptTotalsMatch(snapshot?.total, snapshot?.item_total)
  const mismatch = hasTotal && !matches

  return (
    <div
      data-testid="receipt-group-header"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border bg-muted/40 px-3 py-2 text-sm"
    >
      <span className="font-medium">
        {snapshot?.merchant ?? t("ai.receipts.group.unknownMerchant")}
      </span>
      <span className="text-muted-foreground">
        {snapshot?.purchased_at ?? t("ai.receipts.group.unknownDate")}
      </span>
      {snapshot ? (
        <>
          <span className="text-muted-foreground">
            {t("ai.receipts.group.pages", { count: snapshot.page_count })}
          </span>
          <span className="text-muted-foreground">
            {t("ai.receipts.group.items", { count: itemCount })}
          </span>
          {matches ? (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <CheckCircle2 className="size-3.5" aria-hidden />
              {t("ai.receipts.group.matched")}
            </span>
          ) : null}
          {mismatch ? (
            <span
              role="status"
              className={cn(
                "flex items-center gap-1 text-xs",
                "text-[hsl(var(--warning,32_95%_44%))] dark:text-[hsl(var(--warning,38_92%_60%))]",
              )}
            >
              <AlertTriangle className="size-3.5" aria-hidden />
              {t("ai.receipts.group.mismatch", {
                itemTotal: formatCurrency(snapshot?.item_total, currency, locale),
                total: formatCurrency(snapshot?.total, currency, locale),
                difference: formatCurrency(snapshot?.discrepancy, currency, locale),
              })}
            </span>
          ) : null}
          {!hasTotal ? (
            <span className="text-xs text-muted-foreground">
              {t("ai.receipts.group.noTotal")}
            </span>
          ) : null}
        </>
      ) : (
        <span className="text-muted-foreground">
          {t("ai.receipts.group.items", { count: itemCount })}
        </span>
      )}
    </div>
  )
}
