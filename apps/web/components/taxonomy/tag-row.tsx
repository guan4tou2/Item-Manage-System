"use client"

import { Check, Merge, Pencil, Trash2, X } from "lucide-react"
import { useTranslations } from "next-intl"

import type { TagReadWithCount } from "@/lib/api/tags"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { EditState } from "./tags-panel"

interface TagRowProps {
  tag: TagReadWithCount
  allTags: TagReadWithCount[]
  edit: EditState
  onEditChange: (state: EditState) => void
  onRenameSubmit: (tag: TagReadWithCount, draft: string) => void
  onMergeSubmit: (source: TagReadWithCount, targetId: number) => void
  onDelete: (tag: TagReadWithCount) => void
  renamePending: boolean
  mergePending: boolean
  deletePending: boolean
}

export function TagRow({
  tag,
  allTags,
  edit,
  onEditChange,
  onRenameSubmit,
  onMergeSubmit,
  onDelete,
  renamePending,
  mergePending,
  deletePending,
}: TagRowProps) {
  const t = useTranslations()
  const isRenaming = edit.kind === "rename" && edit.id === tag.id
  const isMerging = edit.kind === "merge" && edit.id === tag.id

  return (
    <li className="flex items-center justify-between gap-2 rounded border px-3 py-2">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        {isRenaming ? (
          <Input
            autoFocus
            value={edit.draft}
            onChange={(e) => onEditChange({ kind: "rename", id: tag.id, draft: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === "Enter") onRenameSubmit(tag, edit.draft)
              if (e.key === "Escape") onEditChange({ kind: "none" })
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
            onClick={() => onRenameSubmit(tag, edit.draft)}
            disabled={renamePending}
            aria-label={t("taxonomy.tags.ariaConfirm")}
          >
            <Check className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEditChange({ kind: "none" })}
            aria-label={t("taxonomy.tags.ariaCancel")}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : isMerging ? (
        <div className="flex gap-1">
          <Select
            value={edit.targetId}
            onValueChange={(v) => onEditChange({ kind: "merge", id: tag.id, targetId: v })}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder={t("taxonomy.tags.selectTarget")} />
            </SelectTrigger>
            <SelectContent>
              {allTags
                .filter((r) => r.id !== tag.id)
                .map((r) => (
                  <SelectItem key={r.id} value={String(r.id)}>
                    {r.name} ({r.item_count})
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => onMergeSubmit(tag, Number(edit.targetId))}
            disabled={!edit.targetId || mergePending}
            aria-label={t("taxonomy.tags.ariaConfirmMerge")}
          >
            <Check className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEditChange({ kind: "none" })}
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
            onClick={() => onEditChange({ kind: "rename", id: tag.id, draft: tag.name })}
            aria-label={t("taxonomy.tags.ariaRename")}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEditChange({ kind: "merge", id: tag.id, targetId: "" })}
            disabled={allTags.length < 2}
            aria-label={t("taxonomy.tags.ariaMerge")}
          >
            <Merge className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(tag)}
            disabled={deletePending}
            aria-label={t("taxonomy.tags.ariaDelete")}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      )}
    </li>
  )
}
