"use client"

import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { useLocale, useTranslations } from "next-intl"

import type { ReceiptSnapshot } from "@/lib/api/ai-receipts"
import { receiptBalanceOf, receiptTotalsMatch } from "@/lib/ai/receipts"
import { formatCurrency } from "@/lib/format/currency"
import { cn } from "@/lib/utils"

interface Props {
  snapshot: ReceiptSnapshot | null
  itemCount: number
}

/**
 * 收據對帳狀態與算術拆解（Phase 38）。
 *
 * - 新版快照（含 `balance_status`）→ 顯示四態判讀＋算術拆解與旗標
 * - 舊快照（無 `balance_status`）→ 沿用 Phase 33 的「總額 vs 品項合計」呈現
 */
export function ReceiptGroupHeader({ snapshot, itemCount }: Props) {
  const t = useTranslations()
  const locale = useLocale()

  const currency = snapshot?.currency ?? "TWD"
  const balance = receiptBalanceOf(snapshot)
  const hasTotal = snapshot?.total !== null && snapshot?.total !== undefined

  // 舊快照：沿用原本的相符／差額判讀
  const legacyMatch =
    hasTotal && receiptTotalsMatch(snapshot?.total, snapshot?.item_total)
  const legacyMismatch = hasTotal && !legacyMatch

  const money = (value: string | null | undefined) =>
    formatCurrency(value ?? null, currency, locale)

  const showEvidence = balance.evidence && hasTotal
  const showBreakdown =
    showEvidence &&
    (balance.status === "balanced" || balance.status === "discrepancy") &&
    balance.calculatedTotal !== null

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

          {/* --- 舊快照：Phase 33 的相符／差額判讀 --- */}
          {!balance.evidence && legacyMatch ? (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <CheckCircle2 className="size-3.5" aria-hidden />
              {t("ai.receipts.group.matched")}
            </span>
          ) : null}
          {!balance.evidence && legacyMismatch ? (
            <span
              role="status"
              className={cn(
                "flex items-center gap-1 text-xs",
                "text-[hsl(var(--warning,32_95%_44%))] dark:text-[hsl(var(--warning,38_92%_60%))]",
              )}
            >
              <AlertTriangle className="size-3.5" aria-hidden />
              {t("ai.receipts.group.mismatch", {
                itemTotal: formatCurrency(snapshot.item_total, currency, locale),
                total: formatCurrency(snapshot.total, currency, locale),
                difference: formatCurrency(snapshot.discrepancy, currency, locale),
              })}
            </span>
          ) : null}
          {!balance.evidence && !hasTotal ? (
            <span className="text-xs text-muted-foreground">
              {t("ai.receipts.group.noTotal")}
            </span>
          ) : null}

          {/* --- 新版快照：四態判讀＋算術拆解（D3） --- */}
          {balance.evidence && balance.status === "balanced" ? (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <CheckCircle2 className="size-3.5" aria-hidden />
              {t("ai.receipts.group.matched")}
            </span>
          ) : null}

          {balance.evidence && balance.status === "discrepancy" ? (
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
                difference: money(balance.discrepancy),
              })}
            </span>
          ) : null}

          {showBreakdown ? (
            <span className="text-xs text-muted-foreground">
              {t("ai.receipts.group.breakdown", {
                itemTotal: money(snapshot?.item_total),
                discount: money(balance.discount),
                tax: money(balance.tax),
                shipping: money(balance.shipping),
                calculated: money(balance.calculatedTotal),
              })}
            </span>
          ) : null}

          {balance.evidence && balance.status === "incomplete" ? (
            <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {balance.missingPriceCount > 0 ? (
                <span>{t("ai.receipts.group.missingPrice", { count: balance.missingPriceCount })}</span>
              ) : null}
              {balance.currencyUnknown ? (
                <span>{t("ai.receipts.group.currencyUnknown")}</span>
              ) : null}
              {balance.uncertainCount > 0 ? (
                <span>{t("ai.receipts.group.uncertain", { count: balance.uncertainCount })}</span>
              ) : null}
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
