"use client"

import { Trash2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"

import type { CategoryTreeNode } from "@/lib/api/categories"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  useCategories, useCreateCategory, useDeleteCategory,
} from "@/lib/hooks/use-categories"

function flatten(nodes: CategoryTreeNode[], depth = 0): Array<{ id: number; label: string; node: CategoryTreeNode }> {
  const out: Array<{ id: number; label: string; node: CategoryTreeNode }> = []
  for (const n of nodes) {
    out.push({ id: n.id, label: `${"— ".repeat(depth)}${n.name}`, node: n })
    out.push(...flatten(n.children ?? [], depth + 1))
  }
  return out
}

export function CategoriesPanel() {
  const t = useTranslations()
  const cats = useCategories()
  const create = useCreateCategory()
  const del = useDeleteCategory()
  const [name, setName] = useState("")
  const [parent, setParent] = useState<string>("none")

  const flat = flatten(cats.data ?? [])

  async function handleAdd() {
    if (!name.trim()) return
    try {
      await create.mutateAsync({
        name: name.trim(),
        parent_id: parent === "none" ? null : Number(parent),
      })
      setName("")
      setParent("none")
    } catch {
      toast.error(t("items.toast.saveFailed"))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("taxonomy.categories.name")}
          aria-label={t("taxonomy.categories.name")}
        />
        <Select value={parent} onValueChange={setParent}>
          <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="none">{t("taxonomy.categories.noParent")}</SelectItem>
            {flat.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={handleAdd} disabled={create.isPending || !name.trim()}>
          {t("taxonomy.categories.add")}
        </Button>
      </div>

      {flat.length === 0 ? (
        <p className="text-muted-foreground">{t("taxonomy.categories.empty")}</p>
      ) : (
        <ul className="space-y-1">
          {flat.map((c) => (
            <li key={c.id} className="flex items-center justify-between border rounded px-3 py-2">
              <span>{c.label}</span>
              <Button
                variant="ghost" size="sm"
                onClick={() => {
                  if (confirm(t("taxonomy.categories.confirmDelete"))) {
                    del.mutate(c.id)
                  }
                }}
                aria-label={t("taxonomy.categories.delete")}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">{t("taxonomy.categories.delete")}</span>
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
