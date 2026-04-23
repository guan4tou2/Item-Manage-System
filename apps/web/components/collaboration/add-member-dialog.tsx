"use client"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAddGroupMember } from "@/lib/hooks/use-groups"

export function AddMemberDialog({ groupId }: { groupId: string }) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState("")
  const [error, setError] = useState<string | null>(null)
  const add = useAddGroupMember(groupId)
  const submit = async () => {
    setError(null)
    try {
      await add.mutateAsync(username.trim())
      setOpen(false); setUsername("")
    } catch {
      setError(t("collab.groups.detail.addMember"))
    }
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm">{t("collab.groups.detail.addMember")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.groups.detail.addMember")}</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <Label>{t("collab.groups.detail.addMemberUsernamePlaceholder")}</Label>
          <Input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={!username.trim() || add.isPending}>{t("lists.new.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
