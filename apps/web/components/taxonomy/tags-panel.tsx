"use client"

import { useTranslations } from "next-intl"
import { useState } from "react"
import { toast } from "sonner"

import type { TagReadWithCount } from "@/lib/api/tags"
import { Button } from "@/components/ui/button"
import {
  useDeleteTag,
  useMergeTag,
  usePruneOrphanTags,
  useRenameTag,
  useTagsWithCounts,
} from "@/lib/hooks/use-tags"
import { TagRow } from "./tag-row"

export type EditState =
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
  const orphanCount = rows.filter((r) => r.item_count === 0).length

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
    const target = rows.find((r) => r.id === targetId)
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
    }
    try {
      await del.mutateAsync({ tagId: tag.id, force: tag.item_count > 0 })
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
          {rows.map((tag) => (
            <TagRow
              key={tag.id}
              tag={tag}
              allTags={rows}
              edit={edit}
              onEditChange={setEdit}
              onRenameSubmit={handleRenameSubmit}
              onMergeSubmit={handleMergeSubmit}
              onDelete={handleDelete}
              renamePending={rename.isPending}
              mergePending={merge.isPending}
              deletePending={del.isPending}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
