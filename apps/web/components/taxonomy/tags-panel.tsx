"use client"

import { Check, Merge, Pencil, Trash2, X } from "lucide-react"
import { useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"

import type { TagReadWithCount } from "@/lib/api/tags"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  useDeleteTag,
  useMergeTag,
  usePruneOrphanTags,
  useRenameTag,
  useTagsWithCounts,
} from "@/lib/hooks/use-tags"

type EditState =
  | { kind: "none" }
  | { kind: "rename"; id: number; draft: string }
  | { kind: "merge"; id: number; targetId: string }

export function TagsPanel() {
  const t = useTranslations()
  const tags = useTagsWithCounts()
  const rename = useRenameTag()
  const merge = useMergeTag()
  const del = useDeleteTag()
  const prune = usePruneOrphanTags()
  const [edit, setEdit] = useState<EditState>({ kind: "none" })

  const rows = tags.data ?? []
  const orphanCount = rows.filter((t) => t.item_count === 0).length

  async function handleRenameSubmit(tag: TagReadWithCount, draft: string) {
    const trimmed = draft.trim()
    if (!trimmed) return
    try {
      await rename.mutateAsync({ tagId: tag.id, name: trimmed })
      toast.success(t("taxonomy.tags.toast.renamed", { name: trimmed.toLowerCase() }))
      setEdit({ kind: "none" })
    } catch (err) {
      const msg = err instanceof Error ? err.message : "rename failed"
      toast.error(msg.includes("409") ? t("taxonomy.tags.toast.renameConflict") : t("taxonomy.tags.toast.renameFailed"))
    }
  }

  async function handleMergeSubmit(source: TagReadWithCount, targetId: number) {
    if (!targetId || targetId === source.id) return
    const target = rows.find((t) => t.id === targetId)
    if (!target) return
    if (!confirm(t("taxonomy.tags.confirmMerge", { source: source.name, target: target.name }))) return
    try {
      const result = await merge.mutateAsync({ sourceId: source.id, targetId })
      toast.success(
        t("taxonomy.tags.toast.merged", { count: result.reassigned_item_count, target: target.name }),
      )
      setEdit({ kind: "none" })
    } catch {
      toast.error(t("taxonomy.tags.toast.mergeFailed"))
    }
  }

  async function handleDelete(tag: TagReadWithCount) {
    if (tag.item_count > 0) {
      if (!confirm(t("taxonomy.tags.confirmForceDelete", { name: tag.name, count: tag.item_count }))) return
      try {
        await del.mutateAsync({ tagId: tag.id, force: true })
        toast.success(t("taxonomy.tags.toast.deleted", { name: tag.name }))
      } catch {
        toast.error(t("taxonomy.tags.toast.deleteFailed"))
      }
      return
    }
    try {
      await del.mutateAsync({ tagId: tag.id, force: false })
      toast.success(t("taxonomy.tags.toast.deleted", { name: tag.name }))
    } catch {
      toast.error(t("taxonomy.tags.toast.deleteFailed"))
    }
  }

  async function handlePrune() {
    if (orphanCount === 0) {
      toast(t("taxonomy.tags.toast.noOrphans"))
      return
    }
    if (!confirm(t("taxonomy.tags.confirmPrune", { count: orphanCount }))) return
    try {
      const result = await prune.mutateAsync()
      toast.success(t("taxonomy.tags.toast.pruned", { count: result.deleted_count }))
    } catch {
      toast.error(t("taxonomy.tags.toast.pruneFailed"))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {t("taxonomy.tags.count", { count: rows.length })}
          {orphanCount > 0 ? t("taxonomy.tags.orphanCount", { count: orphanCount }) : ""}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrune}
          disabled={prune.isPending || orphanCount === 0}
        >
          {t("taxonomy.tags.pruneOrphans")}
        </Button>
      </div>

      {rows.length === 0 ? (
        <p className="text-muted-foreground">{t("taxonomy.tags.empty")}</p>
      ) : (
        <ul className="space-y-1">
          {rows.map((tag) => {
            const isRenaming = edit.kind === "rename" && edit.id === tag.id
            const isMerging = edit.kind === "merge" && edit.id === tag.id
            return (
              <li
                key={tag.id}
                className="flex items-center justify-between gap-2 rounded border px-3 py-2"
              >
                <div className="flex min-w-0 flex-1 items-center gap-2">
                  {isRenaming ? (
                    <Input
                      autoFocus
                      value={edit.draft}
                      onChange={(e) => setEdit({ kind: "rename", id: tag.id, draft: e.target.value })}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleRenameSubmit(tag, edit.draft)
                        if (e.key === "Escape") setEdit({ kind: "none" })
                      }}
                      aria-label={t("taxonomy.tags.ariaNewName")}
                      className="max-w-xs"
                    />
                  ) : (
                    <span className="truncate font-medium">{tag.name}</span>
                  )}
                  <span className="flex-shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                    {t("taxonomy.tags.itemCount", { count: tag.item_count })}
                  </span>
                </div>

                {isRenaming ? (
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      onClick={() => handleRenameSubmit(tag, edit.draft)}
                      disabled={rename.isPending}
                      aria-label={t("taxonomy.tags.ariaConfirm")}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEdit({ kind: "none" })}
                      aria-label={t("taxonomy.tags.ariaCancel")}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : isMerging ? (
                  <div className="flex gap-1">
                    <Select
                      value={edit.targetId}
                      onValueChange={(v) => setEdit({ kind: "merge", id: tag.id, targetId: v })}
                    >
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder={t("taxonomy.tags.selectTarget")} />
                      </SelectTrigger>
                      <SelectContent>
                        {rows
                          .filter((t) => t.id !== tag.id)
                          .map((t) => (
                            <SelectItem key={t.id} value={String(t.id)}>
                              {t.name} ({t.item_count})
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      onClick={() => handleMergeSubmit(tag, Number(edit.targetId))}
                      disabled={!edit.targetId || merge.isPending}
                      aria-label={t("taxonomy.tags.ariaConfirmMerge")}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEdit({ kind: "none" })}
                      aria-label={t("taxonomy.tags.ariaCancel")}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEdit({ kind: "rename", id: tag.id, draft: tag.name })}
                      aria-label={t("taxonomy.tags.ariaRename")}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEdit({ kind: "merge", id: tag.id, targetId: "" })}
                      disabled={rows.length < 2}
                      aria-label={t("taxonomy.tags.ariaMerge")}
                    >
                      <Merge className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(tag)}
                      disabled={del.isPending}
                      aria-label={t("taxonomy.tags.ariaDelete")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
