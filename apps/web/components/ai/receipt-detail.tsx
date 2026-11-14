"use client"

import type { Route } from "next"
import Link from "next/link"
import { useLocale, useTranslations } from "next-intl"

import { ReceiptGroupHeader } from "@/components/ai/receipt-group-header"
import { AuthImage } from "@/components/common/auth-image"
import { ViewerNotice } from "@/components/common/viewer-notice"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { ReceiptRead } from "@/lib/api/ai-receipts"
import { ApiError } from "@/lib/api/client"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { formatCurrency } from "@/lib/format/currency"
import { useReceipt } from "@/lib/hooks/use-ai-receipts"

type Line = ReceiptRead["lines"][number]

/** 整張收據以伺服器快照為準；卡片尚未送出的編輯不會出現在此處。 */
export function ReceiptDetail({ receiptId }: { receiptId: string }) {
  const t = useTranslations()
  const locale = useLocale()
  const readOnly = useReadOnly()
  const query = useReceipt(receiptId)
  const forbidden = query.error instanceof ApiError && query.error.status === 403
  const missing = query.error instanceof ApiError && query.error.status === 404
  const back = <Link href="/items/drafts" className="inline-flex min-h-11 items-center text-sm text-primary underline-offset-4 hover:underline">
    {t("ai.receipts.detail.back")}
  </Link>
  if (readOnly || forbidden) return <section className="p-4 sm:p-6">
    <ViewerNotice backHref="/items" backLabel={t("viewer.notice.backToList")} />
  </section>

  if (query.isPending) return <section className="space-y-6 p-4 sm:p-6" aria-busy="true" aria-label={t("ai.receipts.detail.title")}>
    {back}<Skeleton className="h-16 w-full" /><Skeleton className="h-64 w-full" />
  </section>
  if (query.isError) return <section className="space-y-4 p-4 sm:p-6">
    <h1 className="text-2xl font-semibold">{t("ai.receipts.detail.title")}</h1>
    <p role="alert">{t(missing ? "ai.receipts.detail.notFound" : "ai.receipts.detail.error")}</p>
    {!missing ? <Button variant="outline" onClick={() => query.refetch()}>{t("ai.receipts.detail.retry")}</Button> : null}
    {back}
  </section>
  const data = query.data
  const snapshot = data.snapshot
  const money = (value: string | null | undefined) => formatCurrency(value, snapshot?.currency ?? "XXX", locale)
  const fields = [
    ["item_total", "ai.receipts.detail.amounts.item_total"],
    ["discount", "ai.receipts.detail.amounts.discount"],
    ["tax", "ai.receipts.detail.amounts.tax"],
    ["shipping", "ai.receipts.detail.amounts.shipping"],
    ["calculated_total", "ai.receipts.detail.amounts.calculated_total"],
    ["total", "ai.receipts.detail.amounts.total"],
    ["discrepancy", "ai.receipts.detail.amounts.discrepancy"],
  ] as const
  const statusKeys = {
    pending: "ai.receipts.detail.status.pending",
    processing: "ai.receipts.detail.status.pending",
    ready: "ai.receipts.detail.status.pending",
    accepted: "ai.receipts.detail.status.accepted",
    discarded: "ai.receipts.detail.status.discarded",
    failed: "ai.drafts.status.failed",
  } as const
  const status = (line: Line) => t(statusKeys[line.status])
  const name = (line: Line) => line.status === "accepted" && line.item_id
    ? <Link className="block min-h-11 min-w-11 max-w-full break-words py-3 text-primary underline-offset-4 hover:underline" href={`/items/${line.item_id}` as Route}>{line.name ?? t("ai.drafts.card.untitled")}</Link>
    : line.name ?? t("ai.drafts.card.untitled")
  return <section className="min-w-0 space-y-6 p-4 text-sm sm:p-6">
    {back}
    <h1 className="text-2xl font-semibold">{t("ai.receipts.detail.title")}</h1>
    <ReceiptGroupHeader receiptId={receiptId} snapshot={snapshot ?? null} review={data.review ?? null} itemCount={data.lines.length} showViewLink={false} />
    <section aria-labelledby="receipt-arithmetic" className="space-y-3">
      <h2 id="receipt-arithmetic" className="font-semibold">{t("ai.receipts.detail.arithmetic")}</h2>
      <dl className="max-w-xl divide-y">
        {fields.filter(([field]) => snapshot?.balance_status != null || snapshot?.[field] != null).map(([field, label]) => (
          <div key={field} className="flex items-baseline justify-between gap-4 py-2">
            <dt>{t(label)}</dt>
            <dd className="break-all text-right tabular-nums">{money(snapshot?.[field])}</dd>
          </div>
        ))}
      </dl>
      {!snapshot ? <p className="text-muted-foreground">{t("ai.receipts.detail.noSnapshot")}</p> : null}
    </section>
    <section aria-labelledby="receipt-lines" className="min-w-0 space-y-3">
      <h2 id="receipt-lines" className="font-semibold">{t("ai.receipts.detail.lines")}</h2>
      {data.lines.length === 0 ? <p className="text-muted-foreground">{t("ai.receipts.detail.empty")}</p> : null}
      <div className="hidden md:block">
        <Table>
          <TableHeader><TableRow>
            <TableHead>{t("items.form.name")}</TableHead>
            <TableHead className="text-right">{t("items.form.quantity")}</TableHead>
            <TableHead className="text-right">{t("ai.receipts.detail.unitPrice")}</TableHead>
            <TableHead className="text-right">{t("ai.receipts.detail.subtotal")}</TableHead>
            <TableHead>{t("ai.receipts.detail.statusLabel")}</TableHead>
          </TableRow></TableHeader>
          <TableBody>{data.lines.map((line) => <TableRow key={line.draft_id}>
            <TableCell className="max-w-xs break-words">{name(line)}</TableCell>
            <TableCell className="text-right tabular-nums">{line.quantity ?? "—"}</TableCell>
            <TableCell className="text-right tabular-nums">{money(line.unit_price)}</TableCell>
            <TableCell className="text-right tabular-nums">{money(line.subtotal)}</TableCell>
            <TableCell>{status(line)}</TableCell>
          </TableRow>)}</TableBody>
        </Table>
      </div>
      <ul className="divide-y md:hidden">{data.lines.map((line) => <li key={line.draft_id} className="min-w-0 space-y-2 py-3">
        <div className="flex min-w-0 items-baseline justify-between gap-3">
          <div className="min-w-0 break-words font-medium">{name(line)}</div>
          <span className="shrink-0 text-xs text-muted-foreground">{status(line)}</span>
        </div>
        <dl className="grid grid-cols-3 gap-2 text-xs">
          <div><dt className="text-muted-foreground">{t("items.form.quantity")}</dt><dd className="break-all tabular-nums">{line.quantity ?? "—"}</dd></div>
          <div className="text-right"><dt className="text-muted-foreground">{t("ai.receipts.detail.unitPrice")}</dt><dd className="break-all tabular-nums">{money(line.unit_price)}</dd></div>
          <div className="text-right"><dt className="text-muted-foreground">{t("ai.receipts.detail.subtotal")}</dt><dd className="break-all tabular-nums">{money(line.subtotal)}</dd></div>
        </dl>
      </li>)}</ul>
    </section>
    <section className="space-y-3" aria-labelledby="receipt-image">
      <h2 id="receipt-image" className="font-semibold">{t("ai.receipts.detail.image")}</h2>
      <p className="text-muted-foreground">{t("ai.receipts.detail.firstPage", { count: snapshot?.page_count ?? 1 })}</p>
      {data.image_id ? <AuthImage imageId={data.image_id} alt={t("ai.receipts.detail.image")}
        className="h-auto max-w-full rounded-md border" fallback={<p className="text-muted-foreground">{t("ai.receipts.detail.imageError")}</p>} /> :
        <p className="text-muted-foreground">{t("ai.receipts.detail.imageError")}</p>}
    </section>
  </section>
}
