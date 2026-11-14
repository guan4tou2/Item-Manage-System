"use client"

import { ChevronDown, ChevronRight, Loader2, Minus } from "lucide-react"
import { useLocale, useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"

import { ExpiryBadge } from "./expiry-badge"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import type { BatchRead } from "@/lib/api/batches"
import { getApiErrorDetail } from "@/lib/api/client"
import { useBatches, useConsumeBatch, useCreateBatch, useDisableBatches, useUpdateBatch } from "@/lib/hooks/use-batches"
import { CURRENCY_SYMBOLS, formatCurrency, type Currency } from "@/lib/format/currency"
import { isValidCost, itemCostPayload } from "@/lib/items/cost"
import { itemValuation } from "@/lib/items/valuation"

interface Props {
  itemId: string
  canEdit: boolean
  defaultCost?: string | number | null
  currency?: string
}

export function BatchSection({ itemId, canEdit, defaultCost = null, currency = "TWD" }: Props) {
  const t = useTranslations()
  const locale = useLocale()
  const batches = useBatches(itemId)
  const consume = useConsumeBatch(itemId)
  const disable = useDisableBatches(itemId)
  const [showDepleted, setShowDepleted] = useState(false)
  const [announce, setAnnounce] = useState("")

  if (batches.isLoading) {
    return (
      <section className="max-w-2xl space-y-3">
        <h2 className="text-lg font-medium">{t("items.batches.title")}</h2>
        <Skeleton className="h-16 w-full" />
      </section>
    )
  }

  if (batches.isError) {
    return <section className="max-w-2xl space-y-3">
      <h2 className="text-lg font-medium">{t("items.batches.title")}</h2>
      <p role="alert" className="text-sm text-destructive">{t("items.batches.loadFailed")}</p>
      <Button className="h-11" variant="outline" onClick={() => void batches.refetch()}>{t("items.batches.retry")}</Button>
    </section>
  }

  const rows = batches.data ?? []
  const active = rows.filter((batch) => batch.quantity > 0 && !batch.is_depleted)
  const depleted = rows.filter((batch) => batch.quantity <= 0 || batch.is_depleted)

  const consumeOne = (batch: BatchRead) => {
    consume.mutate(
      { batchId: batch.id, quantity: 1 },
      {
        onSuccess: () => setAnnounce(t("items.batches.consumedAnnounce", { count: 1 })),
        onError: (error) =>
          toast.error(getApiErrorDetail(error) ?? t("items.batches.consumeFailed")),
      },
    )
  }

  const disableTracking = async () => {
    try {
      await disable.mutateAsync()
      toast.success(t("items.batches.disabled"))
      setAnnounce(t("items.batches.disabled"))
    } catch (error) {
      toast.error(getApiErrorDetail(error) ?? t("items.batches.disableFailed"))
    }
  }

  return (
    <section className="max-w-2xl space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-baseline gap-2">
          <h2 className="text-lg font-medium">{t("items.batches.title")}</h2>
          {rows.some((batch) => batch.unit_cost != null) ? (
            <span className="break-all text-sm tabular-nums text-muted-foreground" data-testid="batch-valuation">
              {t("items.batches.subtotal", { amount: formatCurrency(itemValuation(true, 0, defaultCost, rows), currency, locale) })}
            </span>
          ) : null}
        </div>
        {canEdit ? (
          <div className="flex flex-wrap gap-2">
            <BatchDialog itemId={itemId} defaultCost={defaultCost} currency={currency} />
            <DisableBatchesDialog onConfirm={disableTracking} pending={disable.isPending} />
          </div>
        ) : null}
      </div>

      <p aria-live="polite" className="sr-only">
        {announce}
      </p>

      {rows.length === 0 ? (
        <div className="rounded-[0.25rem] border p-4 text-sm text-muted-foreground">
          <p>{t("items.batches.empty")}</p>
          {canEdit ? <p className="mt-1">{t("items.batches.emptyHint")}</p> : null}
        </div>
      ) : (
        <>
          <ul className="divide-y rounded-[0.25rem] border">
            {active.map((batch) => (
              <li
                key={batch.id}
                className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
              >
                <div className="flex min-w-0 flex-wrap items-center gap-2 [overflow-wrap:anywhere]">
                  <span className="tabular-nums">
                    {t("items.batches.remaining", { count: batch.quantity })}
                  </span>
                  {batch.unit_cost != null ? <span className="text-sm tabular-nums text-muted-foreground">{formatCurrency(batch.unit_cost, currency, locale)}</span> : null}
                  {batch.expiry_date ? <ExpiryBadge date={batch.expiry_date} /> : null}
                  {batch.note ? (
                    <span className="text-xs text-muted-foreground">{batch.note}</span>
                  ) : null}
                </div>
                {canEdit ? (
                  <div className="flex flex-wrap gap-2">
                    <BatchDialog itemId={itemId} batch={batch} defaultCost={defaultCost} currency={currency} />
                    <Button
                      type="button"
                      variant="outline"
                      className="h-11 min-w-11 px-3"
                      onClick={() => consumeOne(batch)}
                      aria-label={t("items.batches.consumeOneAria", { quantity: batch.quantity })}
                    >
                      <Minus className="h-4 w-4" aria-hidden="true" />1
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>

          {depleted.length > 0 ? (
            <div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-expanded={showDepleted}
                onClick={() => setShowDepleted((value) => !value)}
              >
                {showDepleted ? (
                  <ChevronDown className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <ChevronRight className="h-4 w-4" aria-hidden="true" />
                )}
                {t("items.batches.depletedToggle", { count: depleted.length })}
              </Button>
              {showDepleted ? (
                <ul className="mt-1 divide-y rounded-[0.25rem] border text-sm text-muted-foreground">
                  {depleted.map((batch) => (
                    <li key={batch.id} className="flex flex-wrap items-center gap-2 px-3 py-2">
                      <span>{t("items.batches.exhausted")}</span>
                      {batch.expiry_date ? <span className="text-xs">{batch.expiry_date}</span> : null}
                      {batch.unit_cost != null ? <span className="tabular-nums">{formatCurrency(batch.unit_cost, currency, locale)}</span> : null}
                      {batch.note ? <span className="min-w-0 break-all text-xs">{batch.note}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </section>
  )
}

function BatchDialog({ itemId, batch, defaultCost, currency }: {
  itemId: string; batch?: BatchRead; defaultCost: string | number | null; currency: string
}) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const locale = useLocale()
  const [quantity, setQuantity] = useState(batch ? String(batch.quantity) : "")
  const [expiryDate, setExpiryDate] = useState(batch?.expiry_date ?? "")
  const [note, setNote] = useState(batch?.note ?? "")
  const [unitCost, setUnitCost] = useState(String(batch?.unit_cost ?? ""))
  const costInvalid = !isValidCost(unitCost)
  const [error, setError] = useState<string | null>(null)
  const create = useCreateBatch(itemId)
  const update = useUpdateBatch(itemId)
  const pending = create.isPending || update.isPending
  const fieldId = `batch-${batch?.id ?? "new"}`

  const submit = async () => {
    if (costInvalid) return
    const parsed = Number(quantity)
    if (!Number.isInteger(parsed) || parsed < 1) {
      setError(t("items.batches.quantityInvalid"))
      return
    }
    setError(null)
    try {
      const body = {
        quantity: parsed,
        expiry_date: expiryDate || null,
        note: note.trim() || null,
        unit_cost: itemCostPayload(unitCost),
      }
      if (batch) await update.mutateAsync({ batchId: batch.id, body })
      else await create.mutateAsync(body)
      toast.success(t(batch ? "items.batches.updated" : "items.batches.created"))
      setOpen(false)
      setQuantity("")
      setExpiryDate("")
      setNote("")
      setUnitCost("")
    } catch (err) {
      toast.error(getApiErrorDetail(err) ?? t(batch ? "items.batches.updateFailed" : "items.batches.createFailed"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => {
      if (next) {
        setQuantity(batch ? String(batch.quantity) : "")
        setExpiryDate(batch?.expiry_date ?? "")
        setNote(batch?.note ?? "")
        setUnitCost(String(batch?.unit_cost ?? ""))
        setError(null)
      }
      setOpen(next)
    }}>
      <DialogTrigger asChild>
        <Button className="h-11" variant={batch ? "outline" : "default"}>{t(batch ? "items.batches.edit" : "items.batches.add")}</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90dvh] w-[calc(100%_-_2rem)] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t(batch ? "items.batches.editTitle" : "items.batches.addTitle")}</DialogTitle>
          <DialogDescription>{t("items.batches.addDescription")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor={`${fieldId}-quantity`}>{t("items.batches.quantity")}</Label>
            <Input
              id={`${fieldId}-quantity`}
              inputMode="numeric"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${fieldId}-expiry`}>{t("items.batches.expiryDate")}</Label>
            <Input
              id={`${fieldId}-expiry`}
              type="date"
              value={expiryDate}
              onChange={(event) => setExpiryDate(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${fieldId}-note`}>{t("items.batches.note")}</Label>
            <Textarea
              id={`${fieldId}-note`}
              rows={2}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${fieldId}-cost`}>{t("items.batches.unitCost", { symbol: CURRENCY_SYMBOLS[currency as Currency] ?? currency })}</Label>
            <Input id={`${fieldId}-cost`} inputMode="decimal" value={unitCost}
              onChange={(event) => setUnitCost(event.target.value)} aria-invalid={costInvalid}
              aria-describedby={`${fieldId}-cost-hint${costInvalid ? ` ${fieldId}-cost-error` : ""}`} />
            <p id={`${fieldId}-cost-hint`} className="text-xs text-muted-foreground">
              {defaultCost != null ? t("items.batches.costFallbackAmount", { amount: formatCurrency(defaultCost, currency, locale) }) : t("items.batches.costFallback")}
            </p>
            {costInvalid ? <p id={`${fieldId}-cost-error`} role="alert" className="text-sm text-destructive">{t("items.form.validation.costInvalid")}</p> : null}
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button className="h-11" variant="outline" onClick={() => setOpen(false)}>
            {t("items.form.cancel")}
          </Button>
          <Button className="h-11" onClick={submit} disabled={pending || costInvalid}>
            {pending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            ) : null}
            {t(batch ? "items.batches.save" : "items.batches.submit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DisableBatchesDialog({
  onConfirm,
  pending,
}: {
  onConfirm: () => void | Promise<void>
  pending: boolean
}) {
  const t = useTranslations()
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" className="h-11" disabled={pending}>
          {t("items.batches.disable")}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("items.batches.disableTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("items.batches.disableBody")}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("items.form.cancel")}</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={pending}>
            {t("items.batches.disable")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
