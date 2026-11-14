"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { ReceiptReview } from "@/lib/api/ai-receipts"
import { useReadOnly } from "@/lib/auth/use-readonly"
import { useReceiptReview } from "@/lib/hooks/use-ai-receipts"

/** 核對為獨立註記；不修改 AI 快照。 */
export function ReceiptReviewActions({ receiptId, review }: {
  receiptId: string
  review: ReceiptReview | null
}) {
  const t = useTranslations()
  const readOnly = useReadOnly()
  const mutation = useReceiptReview(receiptId)
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState("")
  if (readOnly) return null

  const save = (value: string | null | undefined) => {
    setOpen(false)
    mutation.mutate(value, { onError: () => toast.error(t("ai.receipts.review.failed")) })
  }
  return (
    <>
      <Button variant="ghost" className="min-h-11 whitespace-normal" disabled={mutation.isPending}
        onClick={() => {
          if (review) save(undefined)
          else {
            setNote("")
            setOpen(true)
          }
        }}>
        {t(review ? "ai.receipts.review.cancel" : "ai.receipts.review.mark")}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md [&>button]:grid [&>button]:size-11 [&>button]:place-items-center">
          <form className="min-w-0 space-y-4" onSubmit={(event) => { event.preventDefault(); save(note.trim() || null) }}>
            <DialogHeader className="pr-8">
              <DialogTitle>{t("ai.receipts.review.mark")}</DialogTitle>
              <DialogDescription>{t("ai.receipts.review.description")}</DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              <Label htmlFor={`review-note-${receiptId}`}>{t("ai.receipts.review.note")}</Label>
              <Input id={`review-note-${receiptId}`} value={note} maxLength={200}
                aria-describedby={`review-count-${receiptId}`} onChange={(event) => setNote(event.target.value)} />
              <p id={`review-count-${receiptId}`} className="text-right text-xs tabular-nums text-muted-foreground">
                {t("ai.receipts.review.count", { count: note.length })}
              </p>
            </div>
            <DialogFooter><Button type="submit" className="min-h-11">{t("ai.receipts.review.confirm")}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
