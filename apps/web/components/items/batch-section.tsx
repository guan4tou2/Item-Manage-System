"use client"

import { ChevronDown, ChevronRight, Loader2, Minus } from "lucide-react"
import { useTranslations } from "next-intl"
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
import { useBatches, useConsumeBatch, useCreateBatch, useDisableBatches } from "@/lib/hooks/use-batches"

interface Props {
  itemId: string
  canEdit: boolean
}

export function BatchSection({ itemId, canEdit }: Props) {
  const t = useTranslations()
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
        <h2 className="text-lg font-medium">{t("items.batches.title")}</h2>
        {canEdit ? (
          <div className="flex flex-wrap gap-2">
            <CreateBatchDialog itemId={itemId} />
            <DisableBatchesDialog onConfirm={disableTracking} pending={disable.isPending} />
          </div>
        ) : null}
      </div>

      <p aria-live="polite" className="sr-only">
        {announce}
      </p>

      {rows.length === 0 ? (
        <div className="rounded border p-4 text-sm text-muted-foreground">
          <p>{t("items.batches.empty")}</p>
          {canEdit ? <p className="mt-1">{t("items.batches.emptyHint")}</p> : null}
        </div>
      ) : (
        <>
          <ul className="divide-y rounded border">
            {active.map((batch) => (
              <li
                key={batch.id}
                className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="tabular-nums">
                    {t("items.batches.remaining", { count: batch.quantity })}
                  </span>
                  {batch.expiry_date ? <ExpiryBadge date={batch.expiry_date} /> : null}
                  {batch.note ? (
                    <span className="text-xs text-muted-foreground">{batch.note}</span>
                  ) : null}
                </div>
                {canEdit ? (
                  <Button
                    type="button"
                    variant="outline"
                    className="h-11 min-w-11 px-3"
                    onClick={() => consumeOne(batch)}
                    aria-label={t("items.batches.consumeOneAria", { quantity: batch.quantity })}
                  >
                    <Minus className="h-4 w-4" aria-hidden="true" />1
                  </Button>
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
                <ul className="mt-1 divide-y rounded border text-sm text-muted-foreground">
                  {depleted.map((batch) => (
                    <li key={batch.id} className="flex flex-wrap items-center gap-2 px-3 py-2">
                      <span>{t("items.batches.exhausted")}</span>
                      {batch.expiry_date ? <span className="text-xs">{batch.expiry_date}</span> : null}
                      {batch.note ? <span className="text-xs">{batch.note}</span> : null}
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

function CreateBatchDialog({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const [quantity, setQuantity] = useState("")
  const [expiryDate, setExpiryDate] = useState("")
  const [note, setNote] = useState("")
  const [error, setError] = useState<string | null>(null)
  const create = useCreateBatch(itemId)

  const submit = async () => {
    const parsed = Number(quantity)
    if (!Number.isInteger(parsed) || parsed < 1) {
      setError(t("items.batches.quantityInvalid"))
      return
    }
    setError(null)
    try {
      await create.mutateAsync({
        quantity: parsed,
        expiry_date: expiryDate || null,
        note: note.trim() || null,
      })
      toast.success(t("items.batches.created"))
      setOpen(false)
      setQuantity("")
      setExpiryDate("")
      setNote("")
    } catch (err) {
      toast.error(getApiErrorDetail(err) ?? t("items.batches.createFailed"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="h-11">{t("items.batches.add")}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("items.batches.addTitle")}</DialogTitle>
          <DialogDescription>{t("items.batches.addDescription")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="batch-quantity">{t("items.batches.quantity")}</Label>
            <Input
              id="batch-quantity"
              inputMode="numeric"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="batch-expiry">{t("items.batches.expiryDate")}</Label>
            <Input
              id="batch-expiry"
              type="date"
              value={expiryDate}
              onChange={(event) => setExpiryDate(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="batch-note">{t("items.batches.note")}</Label>
            <Textarea
              id="batch-note"
              rows={2}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            {t("items.form.cancel")}
          </Button>
          <Button onClick={submit} disabled={create.isPending}>
            {create.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            ) : null}
            {t("items.batches.submit")}
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
