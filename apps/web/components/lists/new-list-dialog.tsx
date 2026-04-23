"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useCreateList } from "@/lib/hooks/use-lists"
import type { ListKind } from "@/lib/api/lists"

const KINDS: ListKind[] = ["travel", "shopping", "collection", "generic"]

export function NewListDialog() {
  const t = useTranslations()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [kind, setKind] = useState<ListKind>("generic")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const create = useCreateList()

  const submit = async () => {
    if (!title.trim()) return
    const created = await create.mutateAsync({
      kind,
      title: title.trim(),
      description: description.trim() || undefined,
    })
    setOpen(false)
    setTitle("")
    setDescription("")
    setKind("generic")
    router.push(`/lists/${created.id}` as never)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">{t("lists.actions.newList")}</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("lists.actions.newList")}</DialogTitle>
          <DialogDescription>{t("lists.new.titlePlaceholder")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t("lists.new.kindLabel")}</Label>
            <Select value={kind} onValueChange={(v) => setKind(v as ListKind)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {KINDS.map((k) => (
                  <SelectItem key={k} value={k}>
                    {t(`lists.kind.${k}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>{t("lists.new.titlePlaceholder")}</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("lists.new.titlePlaceholder")}
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label>{t("lists.new.descriptionPlaceholder")}</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            {t("lists.new.cancel")}
          </Button>
          <Button onClick={submit} disabled={!title.trim() || create.isPending}>
            {t("lists.new.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
