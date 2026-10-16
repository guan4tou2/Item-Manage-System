"use client"

import { ChevronDown, ChevronRight, MoreHorizontal, Plus, Trash2 } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import type { TreeFlatNode } from "@/lib/locations/tree"
import { cn } from "@/lib/utils"

/** 預設 kind 鍵（其餘視為自由文字，原樣顯示）。 */
const PRESET_KINDS = ["floor", "room", "shelf", "box", "other"]

export interface TreeNodeRowProps {
  node: TreeFlatNode
  depth: number
  hasChildren: boolean
  expanded: boolean
  selected: boolean
  dragging: boolean
  dropTarget: boolean
  dropInvalid: boolean
  isMobile: boolean
  editing: boolean
  draft: string
  onToggle: () => void
  onFocusRow: () => void
  onStartEdit: () => void
  onDraftChange: (value: string) => void
  onCommitEdit: () => void
  onCancelEdit: () => void
  onAddChild: () => void
  onDelete: () => void
  onMoveRequest: () => void
  onDragStart: () => void
  onDragOver: (event: React.DragEvent) => void
  onDrop: () => void
  onDragEnd: () => void
}

/** 位置樹單列：展開收合／行內改名／⋯ 選單／拖放目標／直接物品數。 */
export function TreeNodeRow({
  node,
  depth,
  hasChildren,
  expanded,
  selected,
  dragging,
  dropTarget,
  dropInvalid,
  isMobile,
  editing,
  draft,
  onToggle,
  onFocusRow,
  onStartEdit,
  onDraftChange,
  onCommitEdit,
  onCancelEdit,
  onAddChild,
  onDelete,
  onMoveRequest,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: TreeNodeRowProps) {
  const t = useTranslations()

  return (
    <div
      role="treeitem"
      aria-level={depth + 1}
      aria-expanded={hasChildren ? expanded : undefined}
      aria-selected={selected}
      aria-disabled={dropInvalid || undefined}
      tabIndex={selected ? 0 : -1}
      data-testid={`location-node-${node.id}`}
      data-drop-invalid={dropInvalid || undefined}
      draggable={!isMobile && !editing}
      onDragStart={onDragStart}
      onDragOver={(event) => {
        // 阻斷冒泡：列 hover 的合法性由本列決定，不讓容器（搬到最上層）介入
        event.stopPropagation()
        onDragOver(event)
      }}
      onDrop={(event) => {
        event.preventDefault()
        // 阻斷冒泡：不讓 drop 同時觸發容器的「搬到最上層」（否則兩次 PATCH 競態）
        event.stopPropagation()
        onDrop()
      }}
      onDragEnd={onDragEnd}
      onClick={onFocusRow}
      onFocus={onFocusRow}
      className={cn(
        "flex min-h-11 items-center gap-1 rounded px-2",
        selected && "bg-muted",
        dropTarget && "ring-2 ring-ring",
        dropInvalid && "cursor-not-allowed opacity-50",
        dragging && "opacity-60",
      )}
      title={dropInvalid ? t("locations.tree.invalidTarget") : undefined}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0"
        aria-label={expanded ? t("locations.tree.collapse") : t("locations.tree.expand")}
        aria-hidden={!hasChildren}
        tabIndex={-1}
        disabled={!hasChildren}
        onClick={(event) => {
          event.stopPropagation()
          onToggle()
        }}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )
        ) : (
          <span className="h-4 w-4" />
        )}
      </Button>

      {editing ? (
        <Input
          autoFocus
          value={draft}
          aria-label={t("locations.tree.rename")}
          onChange={(event) => onDraftChange(event.target.value)}
          onBlur={onCommitEdit}
          onKeyDown={(event) => {
            if (event.key === "Enter") onCommitEdit()
            if (event.key === "Escape") onCancelEdit()
          }}
          className="h-8 flex-1"
        />
      ) : (
        <span
          className="min-w-0 flex-1 truncate text-sm"
          onDoubleClick={
            isMobile
              ? undefined
              : (event) => {
                  event.stopPropagation()
                  onStartEdit()
                }
          }
        >
          {node.name}
          {node.kind ? (
            <span className="ml-2 text-xs text-muted-foreground">
              {PRESET_KINDS.includes(node.kind)
                ? t(`locations.kind.${node.kind}`)
                : node.kind}
            </span>
          ) : null}
        </span>
      )}

      {node.item_count > 0 ? (
        <span className="shrink-0 rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
          {t("locations.tree.itemCount", { count: node.item_count })}
        </span>
      ) : null}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            aria-label={t("locations.tree.moreActions", { name: node.name })}
            onClick={(event) => event.stopPropagation()}
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onSelect={onAddChild}>
            <Plus className="mr-2 h-4 w-4" />
            {t("locations.tree.addChild")}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={onStartEdit}>
            {t("locations.tree.rename")}
          </DropdownMenuItem>
          {isMobile ? (
            <DropdownMenuItem onSelect={onMoveRequest}>
              {t("locations.tree.moveTo")}
            </DropdownMenuItem>
          ) : null}
          <DropdownMenuItem onSelect={onDelete}>
            <Trash2 className="mr-2 h-4 w-4" />
            {t("locations.tree.delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
