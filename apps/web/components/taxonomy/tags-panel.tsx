"use client"

import { Check, Merge, Pencil, Trash2, X } from "lucide-react"
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
      toast.success(`已重新命名為 ${trimmed.toLowerCase()}`)
      setEdit({ kind: "none" })
    } catch (err) {
      const msg = err instanceof Error ? err.message : "rename failed"
      toast.error(msg.includes("409") ? "名稱已被其他 tag 使用" : "重新命名失敗")
    }
  }

  async function handleMergeSubmit(source: TagReadWithCount, targetId: number) {
    if (!targetId || targetId === source.id) return
    const target = rows.find((t) => t.id === targetId)
    if (!target) return
    if (!confirm(`將 "${source.name}" 合併到 "${target.name}"？此動作無法復原。`)) return
    try {
      const result = await merge.mutateAsync({ sourceId: source.id, targetId })
      toast.success(
        `合併完成：${result.reassigned_item_count} 個物品已改指向 "${target.name}"`,
      )
      setEdit({ kind: "none" })
    } catch {
      toast.error("合併失敗")
    }
  }

  async function handleDelete(tag: TagReadWithCount) {
    if (tag.item_count > 0) {
      if (!confirm(`"${tag.name}" 仍附加在 ${tag.item_count} 個物品上，確定要強制刪除？`)) return
      try {
        await del.mutateAsync({ tagId: tag.id, force: true })
        toast.success(`已刪除 "${tag.name}"`)
      } catch {
        toast.error("刪除失敗")
      }
      return
    }
    try {
      await del.mutateAsync({ tagId: tag.id, force: false })
      toast.success(`已刪除 "${tag.name}"`)
    } catch {
      toast.error("刪除失敗")
    }
  }

  async function handlePrune() {
    if (orphanCount === 0) {
      toast("沒有孤兒 tag 可清理")
      return
    }
    if (!confirm(`確定要刪除 ${orphanCount} 個沒有物品的 tag？`)) return
    try {
      const result = await prune.mutateAsync()
      toast.success(`已清理 ${result.deleted_count} 個孤兒 tag`)
    } catch {
      toast.error("清理失敗")
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          目前共 {rows.length} 個 tag
          {orphanCount > 0 ? `，其中 ${orphanCount} 個沒有物品使用` : ""}。
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrune}
          disabled={prune.isPending || orphanCount === 0}
        >
          清理孤兒 tag
        </Button>
      </div>

      {rows.length === 0 ? (
        <p className="text-muted-foreground">尚未有任何 tag。從物品頁或 CSV 匯入時建立第一個。</p>
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
                      aria-label="tag 新名稱"
                      className="max-w-xs"
                    />
                  ) : (
                    <span className="truncate font-medium">{tag.name}</span>
                  )}
                  <span className="flex-shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                    {tag.item_count} 個物品
                  </span>
                </div>

                {isRenaming ? (
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      onClick={() => handleRenameSubmit(tag, edit.draft)}
                      disabled={rename.isPending}
                      aria-label="確認"
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEdit({ kind: "none" })}
                      aria-label="取消"
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
                        <SelectValue placeholder="選擇目標 tag" />
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
                      aria-label="確認合併"
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEdit({ kind: "none" })}
                      aria-label="取消"
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
                      aria-label="重新命名"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEdit({ kind: "merge", id: tag.id, targetId: "" })}
                      disabled={rows.length < 2}
                      aria-label="合併到其他 tag"
                    >
                      <Merge className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(tag)}
                      disabled={del.isPending}
                      aria-label="刪除"
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
