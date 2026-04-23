"use client"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useCreateGroup } from "@/lib/hooks/use-groups"

export function NewGroupDialog() {
  const t = useTranslations()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const create = useCreateGroup()
  const submit = async () => {
    if (!name.trim()) return
    const g = await create.mutateAsync({ name: name.trim() })
    setOpen(false); setName("")
    router.push(`/collaboration/groups/${g.id}` as never)
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm">{t("collab.groups.new")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.groups.new")}</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <Label>{t("collab.groups.new")}</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={!name.trim() || create.isPending}>{t("lists.new.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
