"use client"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useCreateTransfer } from "@/lib/hooks/use-transfers"

export function NewTransferDialog({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const [to, setTo] = useState("")
  const [msg, setMsg] = useState("")
  const create = useCreateTransfer()
  const submit = async () => {
    await create.mutateAsync({ item_id: itemId, to_username: to.trim(), message: msg.trim() || undefined })
    setOpen(false); setTo(""); setMsg("")
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="outline">{t("collab.transfer.actions.new")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.transfer.new.title")}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>{t("collab.transfer.new.toUsername")}</Label>
            <Input value={to} onChange={(e) => setTo(e.target.value)} autoFocus />
          </div>
          <div className="space-y-1">
            <Label>{t("collab.transfer.new.message")}</Label>
            <Textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={!to.trim() || create.isPending}>{t("collab.transfer.new.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
