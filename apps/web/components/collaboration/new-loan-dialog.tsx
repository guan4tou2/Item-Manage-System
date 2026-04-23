"use client"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useCreateLoan } from "@/lib/hooks/use-loans"
import type { LoanCreateBody } from "@/lib/api/loans"

export function NewLoanDialog({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<"user" | "label">("label")
  const [user, setUser] = useState("")
  const [label, setLabel] = useState("")
  const [date, setDate] = useState("")
  const [notes, setNotes] = useState("")
  const create = useCreateLoan(itemId)

  const submit = async () => {
    const body: LoanCreateBody = {} as LoanCreateBody
    if (mode === "user" && user.trim()) {
      (body as { borrower_username?: string }).borrower_username = user.trim()
    }
    if (mode === "label" && label.trim()) {
      (body as { borrower_label?: string }).borrower_label = label.trim()
    }
    if (date) (body as { expected_return?: string }).expected_return = date
    if (notes) (body as { notes?: string }).notes = notes
    await create.mutateAsync(body)
    setOpen(false); setUser(""); setLabel(""); setDate(""); setNotes("")
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm">{t("collab.loan.actions.new")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.loan.new.title")}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="flex gap-2">
            <Button size="sm" variant={mode === "user" ? "default" : "outline"} onClick={() => setMode("user")}>
              {t("collab.loan.new.modeUser")}
            </Button>
            <Button size="sm" variant={mode === "label" ? "default" : "outline"} onClick={() => setMode("label")}>
              {t("collab.loan.new.modeLabel")}
            </Button>
          </div>
          {mode === "user" ? (
            <div className="space-y-1">
              <Label>{t("collab.loan.new.borrowerUser")}</Label>
              <Input value={user} onChange={(e) => setUser(e.target.value)} />
            </div>
          ) : (
            <div className="space-y-1">
              <Label>{t("collab.loan.new.borrowerLabel")}</Label>
              <Input value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
          )}
          <div className="space-y-1">
            <Label>{t("collab.loan.new.expectedReturn")}</Label>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>{t("collab.loan.new.notes")}</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={create.isPending || (mode === "user" ? !user.trim() : !label.trim())}>
            {t("collab.loan.new.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
